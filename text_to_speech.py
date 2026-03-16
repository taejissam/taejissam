import asyncio
import os
import re
import sys
from typing import List

# Windows Python 3.11+ asyncio 이벤트 루프 충돌 방지
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def preprocess_for_korean_reading(text: str) -> str:
    replacements = {
        "AI": "에이아이",
        "TTS": "티티에스",
        "GPT": "지피티",
        "%": "퍼센트",
        "cm": "센티미터",
        "mm": "밀리미터",
        "kg": "킬로그램",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

class NaturalKoreanEdgeTTS:
    """
    한국어 자연스러운 TTS 전용 Edge TTS 래퍼.
    포인트:
      - 긴 텍스트를 문장 단위로 나눠서 읽음
      - 쉼표/마침표/줄바꿈 정규화
      - 각 문장 사이에 짧은 무음 구간을 추가
      - 과도한 prosody 변경을 피함
    """

    VOICES = {
        "female": "ko-KR-SunHiNeural",
        "male": "ko-KR-InJoonNeural",
    }

    def __init__(
        self,
        voice: str = "female",
        rate: str = "-2%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
    ):
        self.voice = self.VOICES.get(voice, voice)
        self.rate = rate
        self.volume = volume
        self.pitch = pitch

    def _normalize_text(self, text: str) -> str:
        """발음이 덜 끊기고 더 자연스럽게 들리도록 텍스트 정리"""
        text = text.strip()

        # 줄바꿈/공백 정리
        text = re.sub(r"\s+", " ", text)

        # 문장부호 뒤 공백 정리
        text = re.sub(r"\s*([,.!?])\s*", r"\1 ", text)

        # 너무 많은 반복 부호 제거
        text = re.sub(r"[.]{2,}", "...", text)
        text = re.sub(r"[!]{2,}", "!", text)
        text = re.sub(r"[?]{2,}", "?", text)

        # 괄호는 읽을 때 어색할 수 있어 약하게 정리
        text = text.replace("(", ", ").replace(")", ", ")

        # 콜론/세미콜론은 잠깐 쉬는 느낌으로 변환
        text = text.replace(":", ", ").replace(";", ", ")

        return text.strip()

    def _split_sentences(self, text: str) -> List[str]:
        """
        문장 단위 분리.
        너무 긴 문장은 쉼표 기준으로 한 번 더 분리.
        """
        text = self._normalize_text(text)

        # 문장 단위 분리
        parts = re.split(r"(?<=[.!?])\s+", text)
        sentences = []

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # 너무 긴 문장은 쉼표 기준 추가 분리
            if len(part) > 80 and "," in part:
                subparts = [p.strip() for p in part.split(",") if p.strip()]
                for i, sp in enumerate(subparts):
                    if i < len(subparts) - 1:
                        sentences.append(sp + ",")
                    else:
                        sentences.append(sp)
            else:
                sentences.append(part)

        return sentences

    def _build_ssml(self, sentences: List[str]) -> str:
        """
        문장 사이에 짧은 break를 넣어서 기계적인 붙임 읽기를 줄임.
        """
        body = []
        for i, sent in enumerate(sentences):
            escaped = (
                sent.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
            )

            body.append(
                f"""
                <s>
                    <prosody rate="{self.rate}" pitch="{self.pitch}" volume="{self.volume}">
                        {escaped}
                    </prosody>
                </s>
                """
            )

            # 문장 사이 자연스러운 휴지
            if i < len(sentences) - 1:
                body.append('<break time="450ms"/>')

        ssml = f"""
        <speak version="1.0" xml:lang="ko-KR"
            xmlns="http://www.w3.org/2001/10/synthesis"
            xmlns:mstts="http://www.w3.org/2001/mstts">
            <voice name="{self.voice}">
                {"".join(body)}
            </voice>
        </speak>
        """
        return ssml.strip()

    async def _synthesize(self, text: str, output_path: str):
        try:
            import edge_tts
        except ImportError:
            raise ImportError("edge-tts 미설치. 'pip install edge-tts'를 실행하세요.")

        sentences = self._split_sentences(text)
        if not sentences:
            raise ValueError("비어 있는 텍스트입니다.")

        ssml = self._build_ssml(sentences)

        communicate = edge_tts.Communicate(
            text=ssml,
            voice=self.voice,
        )
        await communicate.save(output_path)

    def save(self, text: str, output_path: str = "output_natural.mp3") -> str:
        _run_async(self._synthesize(text, output_path))
        return os.path.abspath(output_path)


def main():
    text = """
    안녕하세요. 반갑습니다.
    오늘도 좋은 하루 보내세요.
    이것은 한국어 텍스트를 보다 자연스럽게 음성으로 변환하는 예시입니다.
    긴 문장은 한 번에 읽기보다, 적절히 쉬어 가면서 읽는 편이 훨씬 자연스럽게 들립니다.
    """

    print("=" * 50)
    print("자연스러운 한국어 TTS 변환 시작")
    print("=" * 50)

    # 가장 무난하고 자연스러운 추천 설정
    tts = NaturalKoreanEdgeTTS(
        voice="female",   # female 추천
        rate="-2%",       # 너무 빠르지 않게
        pitch="+0Hz",
        volume="+0%"
    )
    path = tts.save(text, "output_natural_female.mp3")
    print(f"저장 완료: {path}")

    # 남성 버전이 필요하면
    tts_male = NaturalKoreanEdgeTTS(
        voice="male",
        rate="-3%",
        pitch="+0Hz",
        volume="+0%"
    )
    text = preprocess_for_korean_reading(text)
    path2 = tts_male.save(text, "output_natural_male.mp3")
    print(f"저장 완료: {path2}")


if __name__ == "__main__":
    main()
