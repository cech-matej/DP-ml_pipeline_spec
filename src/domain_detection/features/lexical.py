"""Reusable lexical feature extraction for training and inference."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
import tldextract

from .contracts import FeatureSchema, FeatureVector


PHISHING_KEYWORDS = [
    "account", "action", "alert", "app", "auth", "bank", "billing", "center", "chat",
    "device", "fax", "event", "find", "free", "gift", "help", "info", "invoice", "live",
    "location", "login", "mail", "map", "message", "my", "new", "nitro", "now", "online",
    "pay", "promo", "real", "required", "safe", "secure", "security", "service", "signin",
    "support", "track", "update", "verification", "verify", "vm", "web",
]
BENIGN_KEYWORDS = [
    "blog", "book", "buy", "community", "design", "dev", "diary", "doc", "download", "edu",
    "family", "forum", "gallery", "game", "health", "home", "host", "lab", "learn", "media",
    "news", "photo", "play", "project", "research", "review", "school", "shop", "site",
    "store", "studio", "tech", "tutorial", "video", "wiki", "work", "safeframe",
    "googlesyndication", "silverhat", "fitcrack", "feta", "vut", "cesnet",
]
TRUSTED_SUFFIXES = ["googlesyndication.com", "office.com", "fbcdn.net", "gstatic.com",
    "yahoodns.net", "pinimg.com", "vut.cz", "vutbr.cz", "cvut.cz", "cuni.cz", "muni.cz",
    "cesnet.cz", "fitcrack.cz"]
WELL_KNOWN_SUFFIXES = ["google.com", "facebook.com", "apple.com", "microsoft.com", "amazon.com",
    "twitter.com", "instagram.com", "linkedin.com", "adobe.com", "spotify.com", "netflix.com",
    "youtube.com", "pinterest.com", "whatsapp.com", "tiktok.com", "wikipedia.org", "mozilla.org",
    "wordpress.org", "bbc.co.uk", "nytimes.com", "reddit.com", "slack.com", "salesforce.com",
    "shopify.com", "dropbox.com", "samsung.com", "oracle.com", "ibm.com", "cisco.com", "zoom.us",
    "paypal.com", "mastercard.com", "visa.com", "stripe.com", "americanexpress.com", "tesla.com",
    "uber.com", "airbnb.com", "tripadvisor.com", "yelp.com", "nasa.gov", "cdc.gov", "who.int",
    "un.org", "europa.eu", "harvard.edu", "stanford.edu", "mit.edu", "cam.ac.uk", "github.com"]
CDN_SUFFIXES = ["akamaihd.net", "akamai.net", "akamaiedge.net", "akamaitechnologies.com",
    "cloudfront.net", "edgecastcdn.net", "fastly.net", "stackpathcdn.com", "cachefly.net",
    "keycdn.com", "cloudflare.net", "maxcdn.com", "cdn77.org", "cdnify.io", "belugacdn.link",
    "kxcdn.com", "cdnetworks.net", "incapdns.net", "lswcdn.net", "llnw.net", "hwcdn.net",
    "nyucd.net", "onappcdn.com", "panthercdn.com", "simplecdn.net", "ssl.hwcdn.net",
    "rncdn1.com", "rlcdn.com", "zenedge.net"]
VPS_SUFFIXES = ["digitalocean.com", "linode.com", "vultr.com", "aws.amazon.com", "azure.com",
    "googleapis.com", "ovh.com", "hetzner.com", "bluehost.com", "hostgator.com", "godaddy.com",
    "dreamhost.com", "siteground.com", "a2hosting.com", "scaleway.com", "upcloud.com",
    "ramnode.com", "inmotionhosting.com", "liquidweb.com", "contabo.com", "cloud.google.com",
    "kamatera.com", "interserver.net", "lunanode.com", "buyvm.net", "time4vps.com",
    "vpsdime.com", "vpsserver.com", "hostwinds.com", "milesweb.com"]
IMAGE_SUFFIXES = ["imgur.com", "flickr.com", "photobucket.com", "500px.com", "postimage.io",
    "tinypic.com", "deviantart.com", "imageshack.us", "imgbb.com", "imgsafe.org", "smugmug.com",
    "imagevenue.com", "imgbox.com", "imgpile.net", "pinterest.com", "pixabay.com", "unsplash.com",
    "pbase.com", "giphy.com", "gyazo.com", "directupload.net", "funkyimg.com", "imagebam.com",
    "cubeupload.com", "photo.net", "dropbox.com", "googleusercontent.com", "mediafire.com",
    "imgflip.com", "ifcdn.com", "img2share.com", "sli.mg", "image.fra.me", "yfrog.com",
    "cloudinary.com", "imgsrc.ru", "instagram.com", "snapfish.com", "shutterfly.com", "tumblr.com",
    "reddituploads.com", "vgy.me", "imageupper.com", "postimg.cc", "imgclick.net",
    "freeimagehosting.net", "imageupload.net", "image-share.com", "pic-upload.de", "imagehosting.com"]
TLD_ABUSE_SCORES = {
    "com": .6554, "net": .1040, "eu": .0681, "name": .0651, "co": .0107, "life": .0087,
    "moe": .0081, "org": .0081, "xyz": .0072, "site": .0051, "ch": .0051, "it": .0048,
    "club": .0046, "info": .0043, "de": .0041, "racing": .0040, "live": .0035, "ru": .0034,
    "cc": .0034, "mobi": .0029, "me": .0023, "au": .0020, "cn": .0019, "pw": .0014,
    "in": .0011, "fr": .0010, "be": .0010, "pro": .0010, "top": .0009, "stream": .0007,
}
IPV4_RE = re.compile(r"(?:(?:25[0-5]|2[0-4]\d|[01]?\d?\d)[.-]){3}(?:25[0-5]|2[0-4]\d|[01]?\d?\d)")


def normalized_entropy(text: str) -> float:
    """Calculate Shannon entropy normalized by the string length.

    :param text: Input text.
    :return: Entropy divided by text length, or zero for empty text.
    """
    if not text:
        return 0.0
    counts = Counter(text)
    return -sum((count / len(text)) * math.log2(count / len(text)) for count in counts.values()) / len(text)


def simhash32(text: str) -> int:
    """Create a stable 32-bit simhash from the characters in a string.

    :param text: Input text.
    :return: Unsigned 32-bit fingerprint represented as an integer.
    """
    votes = [0] * 32
    for char in text:
        value = int(hashlib.md5(char.encode("utf-8")).hexdigest(), 16)
        for bit in range(32):
            votes[bit] += 1 if value & (1 << bit) else -1
    return sum((1 << bit) for bit, vote in enumerate(votes) if vote >= 0)


def ngram_matches(text: str, ngrams: dict[str, Any]) -> int:
    """Count configured n-grams that occur as substrings in text.

    :param text: Text to search.
    :param ngrams: Mapping of n-gram strings to frequencies or values.
    :return: Number of matching n-grams.
    """
    return sum(1 for gram in ngrams if gram in text)


def _suffix_match(domain: str, suffixes: list[str]) -> int:
    """Return one if domain equals a suffix or is its subdomain.

    :param domain: Normalized domain name.
    :param suffixes: Suffixes to check.
    :return: One on a label-boundary match, otherwise zero.
    """
    return int(any(domain == suffix or domain.endswith("." + suffix) for suffix in suffixes))


def _safe_ratio(numerator: int, denominator: int) -> float:
    """Divide safely, returning zero for a zero denominator."""
    return numerator / denominator if denominator else 0.0


class LexicalExtractor:
    """Calculate the legacy lexical feature set and validate it against a schema.

    N-gram JSON files are optional at first boot; absent files produce empty n-gram
    dictionaries. Supply the original files to reproduce the previous feature values.
    """

    def __init__(self, schema: FeatureSchema, data_dir: str | Path = "data"):
        self.schema = schema
        self.data_dir = Path(data_dir)
        self.ngrams: dict[str, dict[str, Any]] = {}
        for family in ("phishing", "malware", "dga"):
            path = self.data_dir / f"ngram_freq_{family}.json"
            self.ngrams[family] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def extract_batch(self, domains: Any) -> pd.DataFrame:
        """Extract only YAML-selected features, in schema order.

        The schema selects features; this module owns their implementations.
        Calculations registered as callables are lazy: they run only when their
        feature is requested. Shared derived values are computed only for groups
        of requested features that need them.
        """

        if isinstance(domains, pd.DataFrame):
            if "domain_name" not in domains.columns:
                raise ValueError("batch input DataFrame must contain domain_name")
            raw = domains["domain_name"].reset_index(drop=True)
        elif isinstance(domains, pd.Series):
            raw = domains.reset_index(drop=True)
        else:
            raw = pd.Series(list(domains), dtype="object")

        if raw.isna().any() or not raw.map(
            lambda value: isinstance(value, str) and bool(value.strip())
        ).all():
            raise ValueError("lexical extractor requires non-empty domain_name strings")

        requested = list(self.schema.features)
        needed = set(requested)
        features = pd.DataFrame(index=raw.index)
        domain = raw.map(lambda value: value.strip().lower().rstrip("."))

        def add(name: str, calculate) -> None:
            """Run a feature calculation only when selected by the YAML schema."""
            if name in needed and name not in features.columns:
                features[name] = calculate()

        # Simple features are kept in a compact registry. Lambdas defer work until
        # add() confirms that the feature is enabled in the active schema.
        simple_calculations = {
            "lex_name_len": lambda: domain.str.len(),
            "lex_has_digit": lambda: domain.str.contains(r"\d", regex=True).astype("int64"),
            "lex_phishing_keyword_count": lambda: domain.map(
                lambda text: sum(word in text for word in PHISHING_KEYWORDS)
            ),
            "lex_benign_keyword_count": lambda: domain.map(
                lambda text: sum(word in text for word in BENIGN_KEYWORDS)
            ),
            "lex_consecutive_chars": lambda: domain.map(
                lambda text: max(
                    (len(match.group()) for match in re.finditer(r"(.)\1*", text)),
                    default=0,
                )
            ),
            "lex_begins_with_digit": lambda: domain.str.match(r"^\d").astype("int64"),
            "lex_www_flag": lambda: domain.str.split(".").map(
                lambda parts: int(parts[0] == "www")
            ),
            "lex_ipv4_in_domain": lambda: domain.str.contains(IPV4_RE, na=False).astype("int64"),
        }
        for name, calculate in simple_calculations.items():
            add(name, calculate)

        # Split-label parsing is shared and lazy: do it only if a selected feature
        # requires a TLD, SLD, subdomain, or n-gram-derived value.
        parsed_feature_names = {
            "lex_tld_len", "lex_tld_abuse_score", "lex_tld_hash",
            "lex_sld_len", "lex_sld_norm_entropy", "lex_sld_digit_count",
            "lex_sld_digit_ratio", "lex_sld_phishing_keyword_count",
            "lex_sld_vowel_count", "lex_sld_vowel_ratio",
            "lex_sld_consonant_count", "lex_sld_consonant_ratio",
            "lex_sld_non_alphanum_count", "lex_sld_non_alphanum_ratio",
            "lex_sld_hex_count", "lex_sld_hex_ratio", "lex_sub_count",
            "lex_stld_unique_char_count", "lex_sub_max_consonant_len",
            "lex_sub_norm_entropy", "lex_sub_digit_count", "lex_sub_digit_ratio",
            "lex_sub_vowel_count", "lex_sub_vowel_ratio",
            "lex_sub_consonant_count", "lex_sub_consonant_ratio",
            "lex_sub_non_alphanum_count", "lex_sub_non_alphanum_ratio",
            "lex_sub_hex_count", "lex_sub_hex_ratio", "lex_shortest_sub_len",
            "lex_phishing_bigram_matches", "lex_phishing_trigram_matches",
            "lex_phishing_tetragram_matches", "lex_phishing_pentagram_matches",
            "lex_malware_bigram_matches", "lex_malware_trigram_matches",
            "lex_malware_tetragram_matches", "lex_dga_bigram_matches",
            "lex_dga_trigram_matches", "lex_dga_tetragram_matches",
        }

        if needed & parsed_feature_names:
            parsed = domain.map(tldextract.extract)
            tld = parsed.map(lambda ext: ext.suffix.lower())
            sld = parsed.map(lambda ext: ext.domain.lower())
            subdomain = parsed.map(lambda ext: ext.subdomain.lower())
            sub_parts = subdomain.map(
                lambda value: [part for part in value.split(".") if part and part != "www"]
            )
            sub_parts = sub_parts.combine(
                sld, lambda subs, second: subs + ([second] if second else [])
            )
            subtext = sub_parts.map("".join)

            for name, calculate in {
                "lex_tld_len": lambda: tld.str.len(),
                "lex_tld_abuse_score": lambda: tld.map(TLD_ABUSE_SCORES).fillna(0.0),
                "lex_tld_hash": lambda: tld.map(simhash32),
                "lex_sld_len": lambda: sld.str.len(),
                "lex_sld_norm_entropy": lambda: sld.map(normalized_entropy),
                "lex_sld_phishing_keyword_count": lambda: sld.map(
                    lambda value: sum(word in value for word in PHISHING_KEYWORDS)
                ),
                "lex_sub_count": lambda: subdomain.map(
                    lambda value: len([
                        part for part in value.split(".") if part and part != "www"
                    ])
                ),
                "lex_stld_unique_char_count": lambda: (sld + tld).map(
                    lambda value: len(set(value.replace(".", "")))
                ),
                "lex_sub_max_consonant_len": lambda: subtext.map(
                    lambda value: max(
                        (len(match.group()) for match in re.finditer(
                            r"[bcdfghjklmnpqrstvwxyz]+", value
                        )),
                        default=0,
                    )
                ),
                "lex_sub_norm_entropy": lambda: subtext.map(normalized_entropy),
                "lex_shortest_sub_len": lambda: sub_parts.map(
                    lambda values: min((len(value) for value in values), default=0)
                ),
            }.items():
                add(name, calculate)

            # Paired count/ratio features share the count and denominator.
            def add_count_ratio(prefix, series, length, pattern, count_name, ratio_name):
                if needed & {count_name, ratio_name}:
                    count = series.str.count(pattern)
                    add(count_name, lambda: count)
                    add(
                        ratio_name,
                        lambda: count.div(length.replace(0, float("nan"))).fillna(0.0),
                    )

            sld_len = sld.str.len()
            add_count_ratio(
                "sld", sld, sld_len, r"\d",
                "lex_sld_digit_count", "lex_sld_digit_ratio"
            )
            add_count_ratio(
                "sld", sld, sld_len, r"[aeiouy]",
                "lex_sld_vowel_count", "lex_sld_vowel_ratio"
            )
            add_count_ratio(
                "sld", sld, sld_len, r"[bcdfghjklmnpqrstvwxyz]",
                "lex_sld_consonant_count", "lex_sld_consonant_ratio"
            )
            if needed & {"lex_sld_non_alphanum_count", "lex_sld_non_alphanum_ratio"}:
                count = sld.map(lambda value: sum(not char.isalnum() for char in value))
                add("lex_sld_non_alphanum_count", lambda: count)
                add(
                    "lex_sld_non_alphanum_ratio",
                    lambda: count.div(sld_len.replace(0, float("nan"))).fillna(0.0),
                )
            add_count_ratio(
                "sld", sld, sld_len, r"[0-9a-f]",
                "lex_sld_hex_count", "lex_sld_hex_ratio"
            )

            sub_len = subtext.str.len()
            add_count_ratio(
                "sub", subtext, sub_len, r"\d",
                "lex_sub_digit_count", "lex_sub_digit_ratio"
            )
            add_count_ratio(
                "sub", subtext, sub_len, r"[aeiouy]",
                "lex_sub_vowel_count", "lex_sub_vowel_ratio"
            )
            add_count_ratio(
                "sub", subtext, sub_len, r"[bcdfghjklmnpqrstvwxyz]",
                "lex_sub_consonant_count", "lex_sub_consonant_ratio"
            )
            if needed & {"lex_sub_non_alphanum_count", "lex_sub_non_alphanum_ratio"}:
                count = subtext.map(lambda value: sum(not char.isalnum() for char in value))
                add("lex_sub_non_alphanum_count", lambda: count)
                add(
                    "lex_sub_non_alphanum_ratio",
                    lambda: count.div(sub_len.replace(0, float("nan"))).fillna(0.0),
                )
            add_count_ratio(
                "sub", subtext, sub_len, r"[0-9a-f]",
                "lex_sub_hex_count", "lex_sub_hex_ratio"
            )

            ngram_specs = {
                "phishing": ("bigram", "trigram", "tetragram", "pentagram"),
                "malware": ("bigram", "trigram", "tetragram"),
                "dga": ("bigram", "trigram", "tetragram"),
            }
            for family, grams in ngram_specs.items():
                for gram in grams:
                    name = f"lex_{family}_{gram}_matches"
                    add(
                        name,
                        lambda family=family, gram=gram: subtext.map(
                            lambda value: ngram_matches(
                                value, self.ngrams[family].get(f"{gram}_freq", {})
                            )
                        ),
                    )

        # Part-length statistics are calculated only if at least one is requested.
        part_names = {
            "lex_avg_part_len", "lex_stdev_part_lens", "lex_longest_part_len",
            "lex_short_part_count", "lex_medium_part_count", "lex_long_part_count",
            "lex_superlong_part_count",
        }
        if needed & part_names:
            part_lengths = domain.str.split(".").map(
                lambda values: [len(part) for part in values]
            )
            for name, calculate in {
                "lex_avg_part_len": lambda lengths: (
                    sum(lengths) / len(lengths) if lengths else 0.0
                ),
                "lex_stdev_part_lens": lambda lengths: (
                    math.sqrt(
                        sum((value - sum(lengths) / len(lengths)) ** 2 for value in lengths)
                        / len(lengths)
                    ) if lengths else 0.0
                ),
                "lex_longest_part_len": lambda lengths: max(lengths, default=0),
                "lex_short_part_count": lambda lengths: sum(value <= 3 for value in lengths),
                "lex_medium_part_count": lambda lengths: sum(
                    4 <= value <= 10 for value in lengths
                ),
                "lex_long_part_count": lambda lengths: sum(
                    11 <= value <= 30 for value in lengths
                ),
                "lex_superlong_part_count": lambda lengths: sum(
                    value >= 31 for value in lengths
                ),
            }.items():
                add(name, lambda calculate=calculate: part_lengths.map(calculate))

        # Suffix flags are registered by name; the score reuses the selected flags.
        suffix_specs = {
            "lex_has_trusted_suffix": TRUSTED_SUFFIXES,
            "lex_has_wellknown_suffix": WELL_KNOWN_SUFFIXES,
            "lex_has_cdn_suffix": CDN_SUFFIXES,
            "lex_has_vps_suffix": VPS_SUFFIXES,
            "lex_has_img_suffix": IMAGE_SUFFIXES,
        }
        if needed & (set(suffix_specs) | {"lex_suffix_score"}):
            for name, suffixes in suffix_specs.items():
                if name in needed or "lex_suffix_score" in needed:
                    add(
                        name,
                        lambda suffixes=suffixes: domain.map(
                            lambda value: _suffix_match(value, suffixes)
                        ),
                    )
            add(
                "lex_suffix_score",
                lambda: (
                    10 * features["lex_has_trusted_suffix"]
                    + 5 * features["lex_has_wellknown_suffix"]
                    + 3 * features["lex_has_cdn_suffix"]
                    + 2 * features["lex_has_vps_suffix"]
                    + 8 * features["lex_has_img_suffix"]
                ),
            )

        missing = needed - set(features.columns)
        if missing:
            raise ValueError(
                "feature implementations missing for configured features: "
                f"{sorted(missing)}"
            )

        features = features.loc[:, requested]
        for name, spec in self.schema.features.items():
            dtype = spec["type"]
            if dtype.startswith("int"):
                features[name] = features[name].astype("int64")
            elif dtype.startswith("float"):
                features[name] = features[name].astype("float64")

        return features

    def extract(self, source: str | dict[str, Any]) -> FeatureVector:
        """Extract one domain through the shared batch implementation.

        :param source: Domain string or mapping containing ``domain_name``.
        :return: Validated FeatureVector using the configured schema.
        """

        domain = source if isinstance(source, str) else source.get("domain_name")
        frame = self.extract_batch([domain])
        values = {
            column: (value.item() if hasattr(value := frame[column].iat[0], "item") else value)
            for column in frame.columns
        }
        validated = self.schema.validate(values)
        return validated
