"""Load any fitted Stage-2 extractor from its directory, so the pipeline never needs to
know which kind it is. Missing or half-written directories fail with a clear message,
never with a silent substitute (in particular: never v1 in place of a transformer)."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


def extractor_kind(directory):
    if os.path.exists(os.path.join(directory, "extractor.json")):
        return "transformer"
    if os.path.exists(os.path.join(directory, "v1_model.joblib")):
        return "v1"
    return None


def load_extractor(directory, device="auto"):
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"extractor directory not found: {directory}")
    kind = extractor_kind(directory)
    if kind == "transformer":
        from extraction.transformer_extractor import TransformerExtractor
        ex = TransformerExtractor.load(directory, device=device)
        if ex.is_joint:
            raise ValueError(f"{directory} is a joint model (Experiment 2); load it with "
                             "sms_pipeline.JointPipeline, not as a Stage-2 extractor")
        return ex
    if kind == "v1":
        from extraction.v1_extractor import V1Extractor
        return V1Extractor.load(directory)
    raise FileNotFoundError(f"{directory} holds no fitted extractor (neither extractor.json "
                            "nor v1_model.joblib); train one first")
