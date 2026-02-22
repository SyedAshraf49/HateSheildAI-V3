import io
from typing import Dict, Tuple

from PIL import Image, ImageStat


class ImagePredictor:
    def __init__(self):
        self._pipeline = None
        self._load_error = None
        self.unsafe_labels = [
            "hate symbol",
            "nazi symbol",
            "racist symbol",
            "violent scene",
            "graphic violence",
            "person holding a gun",
            "person holding a knife",
            "blood",
            "bullying",
            "mocking meme",
            "offensive meme",
            "harassment",
            "threatening message",
            "extremist propaganda",
            "hate speech text",
        ]
        self.safe_labels = [
            "friendly people",
            "neutral meme",
            "wholesome meme",
            "funny meme",
            "cat meme",
            "dog meme",
            "cute cat",
            "cute dog",
            "smiling person",
            "peaceful nature",
            "family photo",
            "educational content",
            "cute animals",
            "positive quote",
            "calm scene",
        ]
        self.emotion_labels = [
            "anger",
            "joy",
            "sadness",
            "fear",
            "disgust",
            "neutral",
        ]

    def _ensure_pipeline(self):
        if self._pipeline is not None or self._load_error is not None:
            return
        try:
            from transformers import pipeline

            self._pipeline = pipeline(
                "zero-shot-image-classification",
                model="openai/clip-vit-base-patch32",
            )
        except Exception as exc:
            self._load_error = str(exc)

    def _open_image(self, image_bytes: bytes) -> Image.Image:
        image = Image.open(io.BytesIO(image_bytes))
        return image.convert("RGB")

    def _fallback_analyze(self, image: Image.Image, filename: str, warning: str = "") -> Dict:
        name = (filename or "").lower()
        unsafe_tokens = [
            "hate", "nazi", "racist", "violence", "violent", "gun", "knife",
            "blood", "bully", "bullying", "mock", "offensive", "abuse", "harass",
        ]
        safe_tokens = [
            "family", "nature", "pet", "cat", "dog", "smile", "happy", "friend",
            "education", "school", "peace", "kind",
        ]

        unsafe_hits = sum(1 for token in unsafe_tokens if token in name)
        safe_hits = sum(1 for token in safe_tokens if token in name)

        stat = ImageStat.Stat(image)
        r_mean, g_mean, b_mean = stat.mean
        brightness = (r_mean + g_mean + b_mean) / 3

        red_dominance = max(0.0, r_mean - ((g_mean + b_mean) / 2))
        blue_dominance = max(0.0, b_mean - ((r_mean + g_mean) / 2))

        unsafe_score = 20 + (unsafe_hits * 20) + min(25, int(red_dominance * 0.45))
        safe_score = 25 + (safe_hits * 18) + (20 if brightness > 150 else 8)

        unsafe_score = max(0, min(95, unsafe_score))
        safe_score = max(0, min(95, safe_score))

        status = "unsafe" if unsafe_score > (safe_score + 10) else "safe"
        confidence = max(35, abs(unsafe_score - safe_score) + 45)
        confidence = min(96, confidence)

        if red_dominance > 25:
            emotion = "anger"
        elif brightness > 170:
            emotion = "joy"
        elif blue_dominance > 20:
            emotion = "sadness"
        elif brightness < 70:
            emotion = "fear"
        else:
            emotion = "neutral"

        response = {
            "filename": filename,
            "status": status,
            "emotion": emotion,
            "emotion_confidence": 60,
            "confidence": confidence,
            "signals": {
                "unsafe_score": unsafe_score,
                "safe_score": safe_score,
                "unsafe_label": "heuristic-unsafe-signal",
                "safe_label": "heuristic-safe-signal",
            },
        }
        if warning:
            response["warning"] = "Using local fallback image analyzer because deep model is unavailable."
            response["details"] = warning
        return response

    @staticmethod
    def _best_label_score(predictions, labels) -> Tuple[str, float]:
        best_label = "unknown"
        best_score = 0.0
        label_set = set(labels)
        for item in predictions:
            label = item.get("label", "")
            score = float(item.get("score", 0.0))
            if label in label_set and score > best_score:
                best_label = label
                best_score = score
        return best_label, best_score

    @staticmethod
    def _group_score(predictions, labels, top_k: int = 4) -> float:
        label_set = set(labels)
        scores = [float(item.get("score", 0.0)) for item in predictions if item.get("label", "") in label_set]
        if not scores:
            return 0.0
        scores.sort(reverse=True)
        return float(sum(scores[:top_k]))

    def analyze_image(self, image_bytes: bytes, filename: str = "") -> Dict:
        self._ensure_pipeline()
        if not image_bytes:
            return {
                "error": "Empty image payload."
            }

        image = self._open_image(image_bytes)

        if self._load_error:
            return self._fallback_analyze(image, filename, warning=self._load_error)

        safety_predictions = self._pipeline(
            image,
            candidate_labels=self.unsafe_labels + self.safe_labels,
        )
        emotion_predictions = self._pipeline(
            image,
            candidate_labels=self.emotion_labels,
        )

        unsafe_label, unsafe_score = self._best_label_score(safety_predictions, self.unsafe_labels)
        safe_label, safe_score = self._best_label_score(safety_predictions, self.safe_labels)
        emotion_label, emotion_score = self._best_label_score(emotion_predictions, self.emotion_labels)

        unsafe_group = self._group_score(safety_predictions, self.unsafe_labels)
        safe_group = self._group_score(safety_predictions, self.safe_labels)

        top_margin = unsafe_score - safe_score
        group_margin = unsafe_group - safe_group

        is_strong_unsafe = unsafe_score >= 0.55
        is_consistent_unsafe = unsafe_score >= 0.40 and top_margin >= 0.18
        is_group_backed = group_margin >= 0.22 and unsafe_group >= 0.55
        is_safely_dominant = safe_score >= 0.45 and safe_group >= unsafe_group and top_margin < 0.10

        if is_safely_dominant:
            status = "safe"
        elif is_strong_unsafe or is_consistent_unsafe or is_group_backed:
            status = "unsafe"
        else:
            status = "safe"

        confidence = int(round(min(98, max(40, (max(unsafe_group, safe_group) * 100) + (abs(group_margin) * 60)))))

        return {
            "filename": filename,
            "status": status,
            "emotion": emotion_label,
            "emotion_confidence": int(round(emotion_score * 100)),
            "confidence": confidence,
            "signals": {
                "unsafe_score": int(round(unsafe_score * 100)),
                "safe_score": int(round(safe_score * 100)),
                "unsafe_group": int(round(unsafe_group * 100)),
                "safe_group": int(round(safe_group * 100)),
                "unsafe_label": unsafe_label,
                "safe_label": safe_label,
            },
        }