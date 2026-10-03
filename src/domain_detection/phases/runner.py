"""Phase composition and bounded batch execution."""
from concurrent.futures import ThreadPoolExecutor

from .contracts import ClassifierResult, DomainResult, PhaseResult


class PhaseRunner:
    def __init__(
        self,
        name,
        version,
        extractors,
        classifiers,
        *,
        parallel_classifiers=True,
        max_concurrent_domains=4,
    ):
        self.name = name
        self.version = version
        self.extractors = extractors
        self.classifiers = classifiers
        self.parallel_classifiers = parallel_classifiers
        self.max_concurrent_domains = max(1, int(max_concurrent_domains))

    def run(self, phase_input):
        def run_domain(domain):
            domain_id = str(domain["domain_id"])
            feature_vectors = {
                name: extractor.extract(self._source_for(name, domain))
                for name, extractor in self.extractors.items()
            }

            def run_classifier(item):
                name, classifier = item
                fv = feature_vectors[classifier.feature_schema]
                prediction = classifier.predict(fv)
                explanation = None
                if phase_input.include_explanations:
                    explanation = classifier.explain(fv, prediction)
                return ClassifierResult(
                    classifier=name,
                    version=classifier.version,
                    prediction=prediction,
                    explanation=explanation,
                )

            items = list(self.classifiers.items())
            if self.parallel_classifiers and len(items) > 1:
                with ThreadPoolExecutor(max_workers=len(items)) as pool:
                    results = list(pool.map(run_classifier, items))
            else:
                results = [run_classifier(item) for item in items]
            return DomainResult(domain_id=domain_id, classifiers=tuple(results))

        domains = list(phase_input.domains)
        if len(domains) > 1 and self.max_concurrent_domains > 1:
            workers = min(self.max_concurrent_domains, len(domains))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                results = list(pool.map(run_domain, domains))
        else:
            results = [run_domain(domain) for domain in domains]

        return PhaseResult(
            phase=self.name,
            version=self.version,
            domains=tuple(results),
        )

    @staticmethod
    def _source_for(extractor_name, domain):
        facts = domain.get("facts", {})
        return facts[extractor_name]
