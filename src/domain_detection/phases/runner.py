from concurrent.futures import ThreadPoolExecutor

from .contracts import ClassifierResult, PhaseResult


class PhaseRunner:
    def __init__(self, name, version, extractors, classifiers, *, parallel_classifiers=True):
        self.name = name
        self.version = version
        self.extractors = extractors
        self.classifiers = classifiers
        self.parallel_classifiers = parallel_classifiers

    def run(self, phase_input):
        feature_vectors = {
            name: extractor.extract(self._source_for(name, phase_input))
            for name, extractor in self.extractors.items()
        }

        def run_classifier(item):
            name, classifier = item
            fv = feature_vectors[classifier.feature_schema]
            prediction = classifier.predict(fv)
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

        return PhaseResult(
            request_id=phase_input.request_id,
            phase=self.name,
            version=self.version,
            classifiers=tuple(results),
        )

    @staticmethod
    def _source_for(extractor_name, phase_input):
        return phase_input.facts[extractor_name]
