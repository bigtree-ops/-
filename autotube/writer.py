"""(선택) 로컬 LLM(Ollama)으로 상품 정보 → 판매용 숏폼 대본 job 파일 자동 작성."""
import json

import requests
import yaml

PROMPT = """너는 SNS 쇼핑 숏폼 영상 대본 전문 카피라이터야.
아래 상품 정보로 30~45초 분량의 한국어 판매 영상 대본을 써줘.

[구성 - 반드시 이 순서]
1. 훅(첫 3초): 스크롤을 멈추게 하는 질문이나 충격적인 한마디
2. 공감: 고객이 겪는 불편/고민
3. 해결: 이 상품이 어떻게 해결하는지
4. 핵심 장점 3가지: 짧고 구체적으로 (숫자, 비교 활용)
5. 신뢰: 후기/판매량/품질 근거 (상품 정보에 있는 것만, 지어내지 말 것)
6. 행동 유도(CTA): 지금 사야 하는 이유 + "프로필 링크 확인" 같은 행동 지시

[문체]
- 친구에게 추천하듯 친근한 구어체, 한 문장은 25자 이내
- 과장 광고, 효능 보장, 최저가 단정 같은 표현 금지

[상품 정보]
{product}

아래 JSON 형식으로만 답해:
{{"title": "유튜브 제목(40자 이내, 핵심 키워드 포함)",
  "description": "영상 설명(3~5줄, 해시태그 3~5개 포함)",
  "tags": ["태그1", "태그2", "..."],
  "scenes": [{{"text": "장면 대사"}}, ...]}}
장면은 6~8개로 나눠줘."""


def write_job(product, images, cfg, avatar=None):
    lcfg = cfg["llm"]
    r = requests.post(f"{lcfg['ollama_url']}/api/generate", json={
        "model": lcfg["model"], "prompt": PROMPT.format(product=product),
        "format": "json", "stream": False, "options": {"temperature": 0.8},
    }, timeout=600)
    r.raise_for_status()
    data = json.loads(r.json()["response"])
    scenes = data["scenes"]
    for i, s in enumerate(scenes):
        if images:
            s["image"] = images[i % len(images)]
    job = {
        "title": data["title"],
        "description": data.get("description", ""),
        "tags": data.get("tags", []),
        "privacy": cfg["youtube"]["default_privacy"],
        "scenes": scenes,
    }
    if avatar:
        job["avatar_image"] = avatar
    return yaml.safe_dump(job, allow_unicode=True, sort_keys=False)
