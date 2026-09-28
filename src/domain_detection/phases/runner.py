from .contracts import ClassifierResult, PhaseResult


class PhaseRunner:
    def __init__(self, name, version, extractors, classifiers):
        self.name = name
        self.version = version
        self.extractors = extractors
        self.classifiers = classifiers

    def run(self, phase_input):
        feature_vectors = {
            name: extractor.extract(self._source_for(name, phase_input))
            for name, extractor in self.extractors.items()
        }

        results = []
        for name, classifier in self.classifiers.items():
            fv = feature_vectors[classifier.feature_schema]
            prediction = classifier.predict(fv)
            explanation = classifier.explain(fv, prediction)
            results.append(
                ClassifierResult(
                    classifier=name,
                    version=classifier.version,
                    prediction=prediction,
                    explanation=explanation,
                )
            )

        return PhaseResult(
            request_id=phase_input.request_id,
            phase=self.name,
            version=self.version,
            classifiers=tuple(results),
        )

    @staticmethod
    def _source_for(extractor_name, phase_input):
        return phase_input.facts[extractor_name]
