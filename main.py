"""
AI 요리 시뮬레이터

개요:
- 자취생, 학생, 1인가구를 대상으로 한 요리 학습 시뮬레이터
- Spoonacular Food API를 연동해 실제 레시피를 가져온다
- 냉장고의 식재료를 관리하고, 조리 도구에 넣어 요리를 만드는 과정 구현
- AI가 보유 재료에 맞는 요리를 추천하고, 최종 요리를 평가해 줌
- 다국어 확장을 쉽게 하기 위해 텍스트를 dict 기반으로 설계

실행 방법:
    python main.py
    python main.py --demo
    python main.py --lang en
    python main.py --api-key YOUR_KEY

주의:
- API 키는 SPOONACULAR_API_KEY 환경 변수 또는 --api-key 옵션으로 설정합니다.
- 네트워크 연결이 되지 않으면 로컬 예시 레시피로 자동 대체됩니다.
- 외부 라이브러리 없이 표준 라이브러리만 사용해 초보자도 수정하기 쉽습니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from typing import Any, Dict, List, Optional, Tuple
import argparse
import json
import logging
import os
import re
import tkinter as tk
from tkinter import messagebox
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


# ---------------------------------------------------------------------------
# 1. Spoonacular Food API 설정
# ---------------------------------------------------------------------------
API_BASE_URL = "https://api.spoonacular.com/recipes/complexSearch"
DEFAULT_API_KEY = os.getenv("SPOONACULAR_API_KEY", "")
RECIPE_SOURCE = "Spoonacular Food API"
RECIPE_SOURCE_URL = "https://spoonacular.com/food-api"
LOGGER = logging.getLogger(__name__)
RECOMMENDATION_LIMIT = 5
LANGUAGE_OPTIONS = {
    "한국어": "ko",
    "English": "en",
    "日本語": "ja",
    "中文": "zh",
}
TRANSLATION_API_URL = "https://translation.googleapis.com/language/translate/v2"


# ---------------------------------------------------------------------------
# 2. 다국어 텍스트 관리
# ---------------------------------------------------------------------------
TEXT = {
    "ko": {
        "title": "AI 요리 시뮬레이터",
        "subtitle": "요리법 학습 · 냉장고 관리 · AI 추천 · 평가",
        "recipe": "레시피",
        "fridge": "냉장고",
        "cooking_area": "조리 공간",
        "ingredient_selection": "식재료 선택",
        "notifications": "알림 및 결과",
        "menu": "메뉴",
        "choose_recipe": "요리 선택",
        "show_recipe": "레시피 보기",
        "recommend": "AI 추천 요리",
        "add_ingredient": "냉장고에 재료 추가",
        "take_ingredient": "냉장고에서 재료 꺼내기",
        "cook": "조리 시작",
        "evaluate": "요리 평가",
        "language": "언어 설정",
        "exit": "종료",
        "invalid": "잘못된 선택입니다.",
        "fresh": "신선한 재료가 준비되었습니다.",
        "no_ingredients": "보유한 재료가 부족합니다.",
        "cook_result": "조리 결과",
        "score": "점수",
        "taste": "맛",
        "completion": "완성도",
        "feedback": "피드백",
        "warning": "주의",
        "thanks": "오늘도 맛있게 요리해 봅시다!",
        "choose_lang": "언어 선택 (ko/en/ja/zh): ",
        "current_lang": "현재 언어",
        "api_loaded": "Spoonacular에서 레시피를 불러왔습니다.",
        "api_fallback": "Spoonacular에서 레시피를 불러오지 못해 로컬 샘플을 사용합니다.",
    },
    "en": {
        "title": "AI Cooking Simulator",
        "subtitle": "Recipe learning · Fridge management · AI recommendation · Evaluation",
        "recipe": "Recipe",
        "fridge": "Fridge",
        "cooking_area": "Cooking Area",
        "ingredient_selection": "Ingredient Selection",
        "notifications": "Alerts & Results",
        "menu": "Menu",
        "choose_recipe": "Choose Recipe",
        "show_recipe": "View Recipe",
        "recommend": "AI Recommended Dish",
        "add_ingredient": "Add ingredient to fridge",
        "take_ingredient": "Take ingredient from fridge",
        "cook": "Start cooking",
        "evaluate": "Evaluate dish",
        "language": "Language",
        "exit": "Exit",
        "invalid": "Invalid selection.",
        "fresh": "Fresh ingredients are ready.",
        "no_ingredients": "Not enough ingredients available.",
        "cook_result": "Cooking Result",
        "score": "Score",
        "taste": "Taste",
        "completion": "Completion",
        "feedback": "Feedback",
        "warning": "Warning",
        "thanks": "Enjoy your cooking today!",
        "choose_lang": "Select language (ko/en/ja/zh): ",
        "current_lang": "Current language",
        "api_loaded": "Recipes were loaded from Spoonacular.",
        "api_fallback": "Could not load Spoonacular recipes. Using local samples instead.",
    },
    "ja": {
        "title": "AI 調理シミュレーター",
        "subtitle": "レシピ学習 · 冷蔵庫管理 · AIおすすめ · 評価",
        "recipe": "レシピ",
        "fridge": "冷蔵庫",
        "cooking_area": "調理スペース",
        "ingredient_selection": "食材選択",
        "notifications": "通知と結果",
        "menu": "メニュー",
        "choose_recipe": "料理を選ぶ",
        "show_recipe": "レシピを見る",
        "recommend": "AIおすすめ料理",
        "add_ingredient": "冷蔵庫に食材を追加",
        "take_ingredient": "冷蔵庫から食材を取り出す",
        "cook": "調理開始",
        "evaluate": "料理を評価",
        "language": "言語",
        "exit": "終了",
        "invalid": "無効な選択です。",
        "fresh": "新鮮な食材が用意されました。",
        "no_ingredients": "食材が不足しています。",
        "cook_result": "調理結果",
        "score": "点数",
        "taste": "味",
        "completion": "完成度",
        "feedback": "フィードバック",
        "warning": "注意",
        "thanks": "今日もおいしく料理しましょう!",
        "choose_lang": "言語を選択してください (ko/en/ja/zh): ",
        "current_lang": "現在の言語",
        "api_loaded": "Spoonacularからレシピを取得しました。",
        "api_fallback": "Spoonacularから取得できなかったため、ローカルのサンプルレシピを使用します。",
    },
    "zh": {
        "title": "AI 烹饪模拟器",
        "subtitle": "食谱学习 · 冰箱管理 · AI推荐 · 评估",
        "recipe": "食谱",
        "fridge": "冰箱",
        "cooking_area": "烹饪区域",
        "ingredient_selection": "食材选择",
        "notifications": "通知与结果",
        "menu": "菜单",
        "choose_recipe": "选择菜品",
        "show_recipe": "查看食谱",
        "recommend": "AI推荐菜品",
        "add_ingredient": "添加食材到冰箱",
        "take_ingredient": "从冰箱取出食材",
        "cook": "开始烹饪",
        "evaluate": "评估菜品",
        "language": "语言",
        "exit": "退出",
        "invalid": "选择无效。",
        "fresh": "新鲜食材已经准备好。",
        "no_ingredients": "食材不足。",
        "cook_result": "烹饪结果",
        "score": "评分",
        "taste": "口味",
        "completion": "完成度",
        "feedback": "反馈",
        "warning": "警告",
        "thanks": "今天也来做一顿好吃的菜吧!",
        "choose_lang": "选择语言 (ko/en/ja/zh): ",
        "current_lang": "当前语言",
        "api_loaded": "已从 Spoonacular 加载食谱。",
        "api_fallback": "无法从 Spoonacular 加载食谱，改用本地示例。",
    },
}


def _(key: str, lang: str = "ko") -> str:
    """간단한 다국어 문자열 가져오기 헬퍼 함수."""
    return TEXT.get(lang, TEXT["ko"]).get(key, key)


# ---------------------------------------------------------------------------
# 3. 기본 데이터 모델
# ---------------------------------------------------------------------------
@dataclass
class Ingredient:
    """재료 하나를 표현하는 클래스."""
    name: str
    category: str
    taste: str = "neutral"
    unit: str = "개"


@dataclass
class Recipe:
    """한 개의 요리 레시피를 표현하는 클래스."""
    name: str
    cuisine: str
    ingredients: List[str]
    tools: List[str]
    steps: List[str]
    taste_profile: str = "balanced"
    difficulty: int = 1
    description: str = ""
    source: str = "local"


# ---------------------------------------------------------------------------
# 4. 로컬 기본 레시피 (API 실패 대비)
# ---------------------------------------------------------------------------
DEFAULT_RECIPES: List[Recipe] = [
    Recipe(
        name="김치볶음밥",
        cuisine="한식",
        ingredients=["김치", "밥", "계란", "양파", "파"],
        tools=["팬", "뒤집개"],
        steps=[
            "팬을 예열하고 양파를 넣어 약불에서 향을 낸다.",
            "김치를 넣고 볶아 숨을 죽인다.",
            "밥을 넣고 고루 섞는다.",
            "계란을 풀어 넣고 휘저어 익힌다.",
            "파를 올려 완성한다."
        ],
        taste_profile="매콤",
        difficulty=2,
        description="매콤한 김치와 고소한 계란이 어우러진 든든한 한 끼",
        source="local"
    ),
    Recipe(
        name="토마토파스타",
        cuisine="이탈리아",
        ingredients=["토마토", "양파", "마늘", "스파게티", "올리브오일"],
        tools=["냄비", "팬"],
        steps=[
            "팬에 올리브오일을 두르고 마늘과 양파를 볶는다.",
            "토마토를 넣고 약한 불로 끓인다.",
            "삶은 스파게티를 넣고 소스를 섞는다.",
            "마지막에 간을 맞춰 완성한다."
        ],
        taste_profile="상큼",
        difficulty=3,
        description="상큼하고 담백한 토마토 소스 파스타",
        source="local"
    ),
    Recipe(
        name="계란볶음밥",
        cuisine="한식",
        ingredients=["밥", "계란", "양파", "당근", "파"],
        tools=["팬", "뒤집개"],
        steps=[
            "팬에 양파와 당근을 살짝 볶는다.",
            "밥을 넣고 고루 섞는다.",
            "계란을 넣고 저어가며 익힌다.",
            "파를 추가해 마무리한다."
        ],
        taste_profile="고소",
        difficulty=1,
        description="간단하고 든든한 계란볶음밥",
        source="local"
    ),
    Recipe(
        name="김치찌개",
        cuisine="한식",
        ingredients=["김치", "두부", "양파", "파"],
        tools=["냄비"],
        steps=[
            "냄비에 김치와 양파를 넣고 볶는다.",
            "물을 붓고 끓인 뒤 두부를 넣는다.",
            "파를 넣고 한소끔 더 끓여 완성한다.",
        ],
        taste_profile="매콤",
        difficulty=2,
        description="김치와 두부를 넣어 끓인 얼큰한 찌개",
        source="local",
    ),
    Recipe(
        name="토마토 달걀볶음",
        cuisine="중식",
        ingredients=["토마토", "계란", "양파", "파"],
        tools=["팬"],
        steps=[
            "토마토와 양파를 먹기 좋게 썬다.",
            "팬에 양파와 토마토를 넣고 볶는다.",
            "계란을 넣고 부드럽게 익힌 뒤 파를 올린다.",
        ],
        taste_profile="고소",
        difficulty=1,
        description="토마토와 달걀을 부드럽게 볶은 간단한 요리",
        source="local",
    ),
]


INGREDIENT_CATALOG: Dict[str, Ingredient] = {
    "토마토": Ingredient("토마토", "채소", "상큼", "개"),
    "양파": Ingredient("양파", "채소", "달콤", "개"),
    "감자": Ingredient("감자", "채소", "고소", "개"),
    "버섯": Ingredient("버섯", "채소", "구수", "컵"),
    "파": Ingredient("파", "채소", "향긋", "대"),
    "계란": Ingredient("계란", "단백질", "고소", "개"),
    "김치": Ingredient("김치", "반찬", "매콤", "컵"),
    "밥": Ingredient("밥", "주식", "부드러움", "공기"),
    "치즈": Ingredient("치즈", "유제품", "진한", "장"),
    "스파게티": Ingredient("스파게티", "면", "부드러움", "인분"),
    "마늘": Ingredient("마늘", "향신료", "매콤", "쪽"),
    "소금": Ingredient("소금", "조미료", "짭짤", "꼬집"),
    "후추": Ingredient("후추", "조미료", "매운", "꼬집"),
    "두부": Ingredient("두부", "단백질", "담백", "모"),
    "참치": Ingredient("참치", "해산물", "고소", "캔"),
    "오징어": Ingredient("오징어", "해산물", "쫄깃", "마리"),
    "고추장": Ingredient("고추장", "소스", "매콤", "스푼"),
    "간장": Ingredient("간장", "소스", "짭짤", "스푼"),
    "올리브오일": Ingredient("올리브오일", "오일", "향긋", "테이블스푼"),
    "당근": Ingredient("당근", "채소", "달콤", "개"),
    "브로콜리": Ingredient("브로콜리", "채소", "상큼", "컵"),
    "베이컨": Ingredient("베이컨", "고기", "짭짤", "장"),
    "우유": Ingredient("우유", "유제품", "부드러움", "컵"),
    "딸기": Ingredient("딸기", "과일", "상큼", "개"),
    "바나나": Ingredient("바나나", "과일", "달콤", "개"),
}


# ---------------------------------------------------------------------------
# 5. Spoonacular API 호출 및 데이터 변환
# ---------------------------------------------------------------------------
class RecipeAPIClient:
    """Spoonacular Food API에서 레시피 데이터를 가져온다."""

    def __init__(self, api_key: str = DEFAULT_API_KEY) -> None:
        self.api_key = api_key

    def fetch(self, limit: int = 10, query: str = "", sort: str = "") -> List[Recipe]:
        """검색어 또는 정렬 기준을 사용해 레시피를 로드한다."""
        if not self.api_key:
            LOGGER.warning("SPOONACULAR_API_KEY가 설정되지 않아 로컬 레시피를 사용합니다.")
            return []

        params = {
            "apiKey": self.api_key,
            "number": max(1, min(limit, 100)),
            "addRecipeInformation": "true",
            "fillIngredients": "true",
            "instructionsRequired": "true",
        }
        if query.strip():
            params["query"] = query.strip()
        if sort:
            params["sort"] = sort
        url = f"{API_BASE_URL}?{urlencode(params)}"

        try:
            with urlopen(url, timeout=15) as response:
                raw = response.read().decode("utf-8")
                payload = json.loads(raw)
        except HTTPError as error:
            LOGGER.warning("Spoonacular API 요청 실패 (HTTP %s).", error.code)
            return []
        except (URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as error:
            LOGGER.warning("Spoonacular API 요청 실패: %s", error)
            return []

        rows = payload.get("results", []) if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            LOGGER.warning("Spoonacular API 응답의 results 형식이 올바르지 않습니다.")
            return []

        recipes: List[Recipe] = []

        for row in rows:
            if not isinstance(row, dict):
                continue
            name = (row.get("title") or "").strip()
            if not name:
                continue

            cuisine = ", ".join(row.get("cuisines") or []) or "기타"
            ingredients = self._extract_ingredients(row.get("extendedIngredients", []))
            steps = self._extract_steps(row)
            description = self._clean_html(row.get("summary") or "")
            if not description:
                ready_minutes = row.get("readyInMinutes")
                description = (
                    f"조리 시간 약 {ready_minutes}분"
                    if ready_minutes
                    else "Spoonacular에서 제공된 레시피입니다."
                )

            recipes.append(
                Recipe(
                    name=name,
                    cuisine=cuisine,
                    ingredients=ingredients or ["재료를 확인하세요"],
                    tools=["팬"],
                    steps=steps or ["레시피 상세를 확인해 주세요."],
                    taste_profile=self._infer_taste(description, " ".join(ingredients)),
                    difficulty=2,
                    description=description,
                    source="spoonacular",
                )
            )

        return recipes

    def _extract_steps(self, row: Dict[str, Any]) -> List[str]:
        """Spoonacular의 분석된 조리 순서 또는 텍스트 안내를 추출한다."""
        steps = []
        instructions = row.get("analyzedInstructions") or []
        if isinstance(instructions, list):
            for instruction_group in instructions:
                if not isinstance(instruction_group, dict):
                    continue
                group_steps = instruction_group.get("steps") or []
                if not isinstance(group_steps, list):
                    continue
                for step in group_steps:
                    if isinstance(step, dict) and isinstance(step.get("step"), str):
                        cleaned = step["step"].strip()
                        if cleaned:
                            steps.append(cleaned)

        if not steps:
            instructions_text = self._clean_html(row.get("instructions") or "")
            steps = [
                step.strip()
                for step in re.split(r"[\r\n]+|(?<=[.!?])\s+", instructions_text)
                if step.strip()
            ]
        return steps

    def _extract_ingredients(self, ingredients: Any) -> List[str]:
        """상세 재료 목록에서 표시용 재료명을 추출한다."""
        if not isinstance(ingredients, list):
            return []
        names = []
        for ingredient in ingredients:
            if not isinstance(ingredient, dict):
                continue
            name = ingredient.get("original") or ingredient.get("name")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
        return names

    def _clean_html(self, text: Any) -> str:
        if not isinstance(text, str):
            return ""
        return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]*>", " ", text))).strip()

    def _infer_taste(self, description: str, ingredient_text: str) -> str:
        """설명 텍스트를 기반으로 맛 프로필을 추정한다."""
        content = (description + " " + ingredient_text).lower()
        if any(word in content for word in ["매콤", "고추", "김치", "불맛", "떡볶이"]):
            return "매콤"
        if any(word in content for word in ["새콤", "상큼", "토마토", "레몬", "산미"]):
            return "상큼"
        if any(word in content for word in ["고소", "버터", "치즈", "달걀", "크림"]):
            return "고소"
        return "balanced"


class TranslationError(RuntimeError):
    """Google Cloud Translation request or response failure."""


class GoogleCloudTranslationClient:
    """Translate UI text with the Google Cloud Translation v2 API."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("GOOGLE_TRANSLATE_API_KEY", "")
        self.cache: Dict[Tuple[str, str], str] = {}

    def translate_many(self, texts: List[str], target_language: str) -> List[str]:
        if target_language == "ko":
            return texts[:]
        if not self.api_key:
            raise TranslationError(
                "GOOGLE_TRANSLATE_API_KEY 환경 변수를 설정한 뒤 앱을 다시 실행하세요."
            )

        results: List[Optional[str]] = [None] * len(texts)
        pending: Dict[str, List[int]] = {}
        for index, text in enumerate(texts):
            cached = self.cache.get((target_language, text))
            if cached is not None:
                results[index] = cached
            else:
                pending.setdefault(text, []).append(index)

        by_source_language: Dict[Optional[str], List[str]] = {}
        for text in pending:
            source_language = self._detect_source_language(text)
            by_source_language.setdefault(source_language, []).append(text)

        for source_language, unique_texts in by_source_language.items():
            for start in range(0, len(unique_texts), 50):
                chunk = unique_texts[start:start + 50]
                translated = self._request(chunk, target_language, source_language)
                for source, translation in zip(chunk, translated):
                    self.cache[(target_language, source)] = translation
                    for index in pending[source]:
                        results[index] = translation

        return [result if result is not None else texts[index] for index, result in enumerate(results)]

    def _detect_source_language(self, text: str) -> Optional[str]:
        if re.search(r"[\uac00-\ud7af]", text):
            return "ko"
        if re.search(r"[\u3040-\u30ff]", text):
            return "ja"
        if re.search(r"[\u4e00-\u9fff]", text):
            return "zh"
        return None

    def cached_translation(self, text: str, target_language: str) -> str:
        return self.cache.get((target_language, text), text)

    def _request(
        self, texts: List[str], target_language: str, source_language: Optional[str]
    ) -> List[str]:
        payload = {"q": texts, "target": target_language, "format": "text"}
        if source_language is not None:
            payload["source"] = source_language
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            TRANSLATION_API_URL,
            data=body,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "X-Goog-Api-Key": self.api_key,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise TranslationError(
                f"Google Cloud Translation 요청 실패 (HTTP {error.code})."
            ) from error
        except (URLError, TimeoutError) as error:
            raise TranslationError(
                f"Google Cloud Translation 연결 실패: {error.reason if isinstance(error, URLError) else error}"
            ) from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise TranslationError("Google Cloud Translation 응답을 읽을 수 없습니다.") from error

        translations = (
            payload.get("data", {}).get("translations")
            if isinstance(payload, dict)
            else None
        )
        if not isinstance(translations, list) or len(translations) != len(texts):
            raise TranslationError("Google Cloud Translation 응답 형식이 올바르지 않습니다.")
        translated_texts = []
        for item in translations:
            if not isinstance(item, dict) or not isinstance(item.get("translatedText"), str):
                raise TranslationError("번역 결과에 올바르지 않은 항목이 있습니다.")
            translated_texts.append(unescape(item["translatedText"]))
        return translated_texts


# ---------------------------------------------------------------------------
# 6. 실제 로드 함수
# ---------------------------------------------------------------------------
def load_recipes(
    api_key: str = DEFAULT_API_KEY,
    limit: int = 10,
    query: str = "",
) -> List[Recipe]:
    """API 호출을 시도하고 실패하면 검색어에 맞는 로컬 레시피를 반환한다."""
    recipes = RecipeAPIClient(api_key).fetch(limit=limit, query=query)
    if recipes:
        return recipes
    if query.strip():
        term = query.strip().casefold()
        return [
            recipe for recipe in DEFAULT_RECIPES
            if term in recipe.name.casefold() or term in recipe.description.casefold()
        ]
    return DEFAULT_RECIPES


# ---------------------------------------------------------------------------
# 7. 냉장고 관리 로직
# ---------------------------------------------------------------------------
class Fridge:
    """냉장고는 식재료를 저장하고 꺼내는 핵심 저장소입니다."""

    def __init__(self) -> None:
        self.inventory: Dict[str, int] = {
            "토마토": 2,
            "양파": 2,
            "계란": 4,
            "김치": 1,
            "밥": 2,
            "파": 2,
            "마늘": 1,
            "올리브오일": 1,
            "두부": 1,
            "치즈": 1,
            "스파게티": 1,
            "당근": 1,
            "버섯": 1,
            "우유": 1,
        }

    def add_item(self, ingredient_name: str, quantity: int = 1) -> str:
        """냉장고에 재료 추가"""
        if ingredient_name not in INGREDIENT_CATALOG:
            return f"'{ingredient_name}'은(는) 등록된 재료가 아닙니다."

        self.inventory[ingredient_name] = self.inventory.get(ingredient_name, 0) + quantity
        return f"{ingredient_name} {quantity}개를 냉장고에 보관했습니다."

    def take_item(self, ingredient_name: str, quantity: int = 1) -> str:
        """냉장고에서 재료 꺼내기"""
        if ingredient_name not in self.inventory:
            return f"{ingredient_name}은(는) 냉장고에 없습니다."
        if self.inventory[ingredient_name] < quantity:
            return f"{ingredient_name}이(가) 부족합니다. 현재 {self.inventory[ingredient_name]}개 보유."

        self.inventory[ingredient_name] -= quantity
        if self.inventory[ingredient_name] == 0:
            del self.inventory[ingredient_name]
        return f"{ingredient_name} {quantity}개를 꺼냈습니다."

    def list_items(self) -> List[str]:
        """냉장고의 저장된 재료 목록 반환"""
        if not self.inventory:
            return ["냉장고가 비어 있습니다."]
        return [f"{name}: {count}개" for name, count in sorted(self.inventory.items())]

    def has_ingredients(self, ingredient_names: List[str]) -> bool:
        """추천용으로 재료 보유 여부를 확인한다. 실제 조리는 수량 제한 없이 시작한다."""
        for name in ingredient_names:
            if self.inventory.get(name, 0) <= 0:
                return False
        return True


# ---------------------------------------------------------------------------
# 8. 조리 도구 / 조리 공간 로직
# ---------------------------------------------------------------------------
class CookingSimulation:
    """조리 공간의 실제 동작을 관리합니다."""

    def __init__(self) -> None:
        self.tray: List[str] = []
        self.tools: Dict[str, List[str]] = {
            "냄비": [],
            "팬": [],
            "도마": [],
            "그릇": [],
        }
        self.selected_recipe: Optional[Recipe] = None
        self.cooking_log: List[str] = []

    def set_recipe(self, recipe: Recipe) -> None:
        """선택된 레시피를 저장"""
        self.selected_recipe = recipe
        self.cooking_log = [f"'{recipe.name}' 요리를 준비합니다."]

    def put_in_tool(self, tool_name: str, ingredient_name: str) -> str:
        """재료를 조리 도구에 넣는 동작. 텍스트 기반 drag & drop."""
        if tool_name not in self.tools:
            return f"'{tool_name}'은(는) 지원하지 않는 조리 도구입니다."

        if ingredient_name and ingredient_name not in INGREDIENT_CATALOG:
            return f"'{ingredient_name}'은(는) 등록되지 않은 재료입니다."

        self.tools[tool_name].append(ingredient_name)
        self.cooking_log.append(f"{ingredient_name}을(를) {tool_name}에 넣었습니다.")
        return f"{ingredient_name}이(가) {tool_name}에 넣어졌습니다."

    def clear_tool(self, tool_name: str) -> str:
        """조리 도구 비우기"""
        if tool_name not in self.tools:
            return f"'{tool_name}'은(는) 지원하지 않는 조리 도구입니다."
        self.tools[tool_name].clear()
        self.cooking_log.append(f"{tool_name}을(를) 비웠습니다.")
        return f"{tool_name}이(가) 비워졌습니다."

    def simulate_cooking(self, recipe: Optional[Recipe] = None) -> Dict[str, object]:
        """선택한 요리를 실제로 조리하는 시뮬레이션.

        냉장고 재료는 추천용으로만 사용하고, 조리 시작은 수량 제한 없이 가능하게 한다.
        """
        target_recipe = recipe or self.selected_recipe
        if target_recipe is None:
            return {"success": False, "message": "선택된 요리가 없습니다.", "steps": []}

        result = {
            "success": True,
            "recipe": target_recipe.name,
            "steps": target_recipe.steps[:],
            "message": f"{target_recipe.name} 조리가 시작되었습니다."
        }

        # 게임 흐름상 실제 조리는 재고 수량보다 요리 진행 자체를 우선한다.
        # 재료의 보유 여부는 추천 로직에서만 활용한다.
        self.cooking_log.append(result["message"])
        return result

    def prepare_from_fridge(self, fridge: Fridge, ingredient_name: str, tool_name: str = "팬") -> str:
        """냉장고 재료를 꺼내서 조리 도구에 넣는 흐름을 구현.

        추천은 냉장고 재고를 기반으로 하지만, 조리 자체는 재료 수량과 무관하게 시작 가능하게 한다.
        """
        if ingredient_name not in INGREDIENT_CATALOG:
            return f"'{ingredient_name}'은(는) 등록되지 않은 재료입니다."
        if ingredient_name not in fridge.inventory:
            fridge.inventory[ingredient_name] = fridge.inventory.get(ingredient_name, 0) + 1
        self.put_in_tool(tool_name, ingredient_name)
        return f"{ingredient_name}을(를) 조리 도구에 준비했습니다."


# ---------------------------------------------------------------------------
# 9. AI 추천 로직
# ---------------------------------------------------------------------------
class AIKitchenAssistant:
    """사용자의 재료 조합과 취향을 기반으로 레시피를 추천하는 AI."""

    INGREDIENT_ALIASES = {
        "토마토": ("tomato", "tomatoes"),
        "양파": ("onion", "onions"),
        "감자": ("potato", "potatoes"),
        "버섯": ("mushroom", "mushrooms"),
        "파": ("green onion", "spring onion", "scallion", "leek"),
        "계란": ("egg", "eggs"),
        "김치": ("kimchi",),
        "밥": ("rice",),
        "치즈": ("cheese",),
        "스파게티": ("spaghetti", "pasta"),
        "마늘": ("garlic",),
        "소금": ("salt",),
        "후추": ("pepper",),
        "두부": ("tofu",),
        "참치": ("tuna",),
        "오징어": ("squid",),
        "고추장": ("gochujang",),
        "간장": ("soy sauce",),
        "올리브오일": ("olive oil",),
        "당근": ("carrot", "carrots"),
        "브로콜리": ("broccoli",),
        "베이컨": ("bacon",),
        "우유": ("milk",),
        "딸기": ("strawberry", "strawberries"),
        "바나나": ("banana", "bananas"),
    }

    def __init__(self) -> None:
        self.preferred_taste = "balanced"
        self.used_popular_fallback = False

    def recommend(
        self,
        fridge: Fridge,
        recipes: Optional[List[Recipe]] = None,
        preferred_taste: str = "balanced",
        api_key: str = DEFAULT_API_KEY,
        limit: int = RECOMMENDATION_LIMIT,
    ) -> List[Recipe]:
        """만들 수 있는 요리를 최대 5개 추천하고, 없으면 인기 요리를 추천한다."""
        self.preferred_taste = preferred_taste
        candidates = list(recipes if recipes is not None else RECIPES)
        candidates.extend(DEFAULT_RECIPES)
        cookable: List[Recipe] = []
        seen_names = set()
        for recipe in candidates:
            if not recipe.ingredients or not all(
                self._ingredient_is_available(ingredient, fridge)
                for ingredient in recipe.ingredients
            ):
                continue
            name_key = recipe.name.casefold()
            if name_key not in seen_names:
                seen_names.add(name_key)
                cookable.append(recipe)
        if cookable:
            self.used_popular_fallback = False
            return sorted(
                cookable,
                key=lambda recipe: (
                    recipe.taste_profile not in self._preferred_tastes(preferred_taste),
                    recipe.difficulty,
                    recipe.name.casefold(),
                ),
            )[:max(1, limit)]

        self.used_popular_fallback = True
        popular = RecipeAPIClient(api_key).fetch(
            limit=max(1, limit),
            sort="popularity",
        )
        popular.extend(DEFAULT_RECIPES)
        popular_unique: List[Recipe] = []
        seen_names.clear()
        for recipe in popular:
            name_key = recipe.name.casefold()
            if name_key not in seen_names:
                seen_names.add(name_key)
                popular_unique.append(recipe)
            if len(popular_unique) >= max(1, limit):
                break
        return popular_unique

    def _ingredient_is_available(self, recipe_ingredient: str, fridge: Fridge) -> bool:
        normalized = recipe_ingredient.casefold()
        for available, quantity in fridge.inventory.items():
            if quantity <= 0:
                continue
            if available.casefold() in normalized:
                return True
            aliases = self.INGREDIENT_ALIASES.get(available, ())
            for alias in aliases:
                if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", normalized):
                    return True
        return False

    @staticmethod
    def _preferred_tastes(preferred_taste: str) -> List[str]:
        taste_aliases = {
            "spicy": ["매콤", "spicy"],
            "savory": ["고소", "savory"],
            "refreshing": ["상큼", "refreshing"],
            "balanced": ["고소", "상큼", "매콤", "balanced"],
        }
        return taste_aliases.get(preferred_taste, [preferred_taste])


# ---------------------------------------------------------------------------
# 10. 평가 로직
# ---------------------------------------------------------------------------
class RecipeEvaluator:
    """완성된 요리에 대한 맛, 완성도, 피드백을 계산한다."""

    def evaluate(
        self,
        recipe: Recipe,
        selected_ingredients: List[str],
        process_steps: List[str],
        taste_profile: str = "balanced",
    ) -> Dict[str, object]:
        matched = sum(1 for ing in recipe.ingredients if ing in selected_ingredients)
        ingredient_ratio = matched / max(len(recipe.ingredients), 1)
        process_ratio = min(len(process_steps) / max(len(recipe.steps), 1), 1.0)

        flavor_bonus = 0
        if taste_profile == "balanced":
            flavor_bonus = 10
        elif taste_profile in ["spicy", "매콤"] and recipe.taste_profile in ["매콤", "spicy"]:
            flavor_bonus = 15
        elif taste_profile in ["savory", "고소"] and recipe.taste_profile in ["고소", "savory"]:
            flavor_bonus = 15
        elif taste_profile in ["refreshing", "상큼"] and recipe.taste_profile in ["상큼", "refreshing"]:
            flavor_bonus = 15

        total_score = int((ingredient_ratio * 60) + (process_ratio * 25) + flavor_bonus)
        total_score = max(0, min(total_score, 100))

        if total_score >= 85:
            taste_text = "매우 맛있다"
            completion = "완성도 높음"
            feedback = "식감과 밸런스가 훌륭합니다. 다음에도 이 조합으로 만들면 좋습니다."
        elif total_score >= 70:
            taste_text = "좋은 편이다"
            completion = "대체로 완성됨"
            feedback = "재료의 조합은 좋지만, 간과 조리 시간을 조금 더 조정하면 더 맛있어집니다."
        elif total_score >= 50:
            taste_text = "보통이다"
            completion = "조금 더 보완 필요"
            feedback = "기본 맛은 괜찮지만, 재료를 더 신선하게 넣거나 조리 시간을 늘려보세요."
        else:
            taste_text = "아쉬운 편이다"
            completion = "재조정 필요"
            feedback = "레시피와 재료의 조합이 많이 어긋났습니다. 재료를 다시 확인해 보세요."

        return {
            "score": total_score,
            "taste": taste_text,
            "completion": completion,
            "feedback": feedback,
            "matched_count": matched,
            "required_count": len(recipe.ingredients),
        }


# ---------------------------------------------------------------------------
# 11. 콘솔 기반 UI
# ---------------------------------------------------------------------------
class KitchenUI:
    """시뮬레이터 화면을 콘솔 형태로 보여주는 클래스입니다."""

    def __init__(self, lang: str = "ko") -> None:
        self.lang = lang

    def print_header(self, title: str = "") -> None:
        """상단 영역: 레시피 및 타이틀"""
        print("=" * 100)
        print(f"{_('title', self.lang):>30}")
        if title:
            print(f"{title}")
        print(f"{_('subtitle', self.lang)}")
        print("=" * 100)

    def print_recipe_panel(self, recipe: Optional[Recipe]) -> None:
        """상단 레시피 표시"""
        print(f"\n[ {_('recipe', self.lang)} ]")
        if recipe is None:
            print("추천된 레시피가 아직 없습니다.")
            return

        print(f"요리명: {recipe.name}")
        print(f"종류: {recipe.cuisine}")
        print(f"설명: {recipe.description}")
        print(
            f"출처: {RECIPE_SOURCE} ({RECIPE_SOURCE_URL})"
            if recipe.source == "spoonacular"
            else "출처: 로컬 샘플 데이터"
        )
        print(f"필수 재료: {', '.join(recipe.ingredients)}")
        print("조리 순서:")
        for idx, step in enumerate(recipe.steps, start=1):
            print(f"  {idx}. {step}")

    def print_cooking_area(self, sim: CookingSimulation) -> None:
        """중앙 영역: 조리 공간"""
        print(f"\n[ {_('cooking_area', self.lang)} ]")
        for tool_name, items in sim.tools.items():
            print(f"{tool_name}: {', '.join(items) if items else '비어 있음'}")

    def print_fridge(self, fridge: Fridge) -> None:
        """우측 영역: 냉장고 목록"""
        print(f"\n[ {_('fridge', self.lang)} ]")
        for item in fridge.list_items():
            print(f" - {item}")

    def print_bottom_panel(self, message: str = "") -> None:
        """하단 영역: 입력/결과/알림"""
        print(f"\n[ {_('notifications', self.lang)} ]")
        if message:
            print(message)
        else:
            print("시스템이 준비 중입니다. 메뉴를 선택해 주세요.")

    def print_menu(self) -> None:
        """메인 메뉴를 출력."""
        print(f"\n[ {_('menu', self.lang)} ]")
        print("1. 레시피 보기")
        print("2. AI 추천 요리")
        print("3. 냉장고 재료 추가")
        print("4. 냉장고에서 재료 꺼내기")
        print("5. 조리 도구에 재료 넣기")
        print("6. 조리 시작")
        print("7. 요리 평가")
        print("8. 언어 설정")
        print("9. 종료")


class CookingGameGUI(tk.Tk):
    """실제 게임처럼 보이는 GUI 인터페이스."""

    def __init__(self, lang: str = "ko", api_key: str = DEFAULT_API_KEY) -> None:
        super().__init__()
        self.lang = "ko"
        self.requested_lang = lang if lang in {"ko", "en", "ja", "zh"} else "ko"
        self.api_key = api_key
        self.translator = GoogleCloudTranslationClient()
        self._ui_text_sources: Dict[Tuple[Any, ...], str] = {}
        self._ui_text_rendered: Dict[Tuple[Any, ...], str] = {}
        self._ui_sequence_sources: Dict[Tuple[Any, ...], Tuple[str, ...]] = {}
        self._ui_sequence_rendered: Dict[Tuple[Any, ...], Tuple[str, ...]] = {}
        self._ui_string_vars: List[tk.StringVar] = []
        self._ui_translation_pending = False
        self._ui_translation_applying = False
        self.title(_("title", self.lang))
        self.geometry("1280x820")
        self.minsize(1000, 580)
        self.configure(bg="#f4efe7")
        self._global_wheel_widget = None

        self.all_recipes = load_recipes(api_key, limit=10)
        self.recipes = self.all_recipes[:]
        self.fridge = Fridge()
        self.sim = CookingSimulation()
        self.assistant = AIKitchenAssistant()
        self.evaluator = RecipeEvaluator()
        self.current_recipe: Optional[Recipe] = None
        self.selected_ingredient: Optional[str] = None
        self.selected_tool: str = "팬"
        self.cooking_started = False
        self.current_step_index = 0
        self.knife_dragging = False
        self.knife_anchor = (0, 0)
        self.dragged_tag: Optional[str] = None
        self.drag_anchor = (0, 0)
        self.scene_ingredient_by_tag: Dict[str, str] = {}
        self.scene_cut_indices = set()
        self.game_opened = False
        self.remaining_seconds = 180
        self.timer_after_id: Optional[str] = None
        self.heat_level = 2
        self.time_limit = 180

        self._build_ui()
        self.refresh_recipe_list()
        self.refresh_fridge()
        self.update_tool_panel()
        self.update_recipe_guide()
        api_status = (
            _("api_loaded", self.lang)
            if any(recipe.source == "spoonacular" for recipe in self.recipes)
            else _("api_fallback", self.lang)
        )
        self.status_var.set(f"{api_status} 요리를 선택해 보세요.")
        if self.requested_lang != "ko":
            self._apply_language(self.requested_lang)

    def _build_ui(self) -> None:
        scroll_container = tk.Frame(self, bg="#f4efe7")
        scroll_container.pack(fill=tk.BOTH, expand=True)
        self.page_canvas = tk.Canvas(
            scroll_container,
            bg="#f4efe7",
            highlightthickness=0,
            yscrollincrement=24,
        )
        self.page_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.page_scrollbar = tk.Scrollbar(
            scroll_container,
            orient=tk.VERTICAL,
            command=self.page_canvas.yview,
        )
        self.page_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.page_canvas.configure(yscrollcommand=self.page_scrollbar.set)

        page = tk.Frame(self.page_canvas, bg="#f4efe7")
        self.page_window = self.page_canvas.create_window(
            (0, 0), window=page, anchor="nw"
        )
        page.bind("<Configure>", self._update_page_scrollregion)
        self.page_canvas.bind("<Configure>", self._resize_page_content)
        self.bind_all("<MouseWheel>", self._on_page_mousewheel, add="+")
        self.bind_all("<Button-4>", self._on_page_mousewheel, add="+")
        self.bind_all("<Button-5>", self._on_page_mousewheel, add="+")
        self.bind_all("<ButtonRelease-1>", self._queue_ui_translation, add="+")
        self.bind_all("<Return>", self._queue_ui_translation, add="+")
        self.bind_all("<<ListboxSelect>>", self._queue_ui_translation, add="+")

        main = tk.Frame(page, bg="#f4efe7", padx=16, pady=16)
        main.pack(fill=tk.X, expand=True)

        header = tk.Label(
            main,
            text=_("title", self.lang),
            font=("Malgun Gothic", 22, "bold"),
            bg="#f4efe7",
            fg="#4a2c15",
        )
        header.pack(anchor="w", pady=(0, 6))

        subtitle = tk.Label(
            main,
            text=_("subtitle", self.lang),
            font=("Malgun Gothic", 11),
            bg="#f4efe7",
            fg="#6a4c35",
        )
        subtitle.pack(anchor="w", pady=(0, 12))

        self.start_button = tk.Button(
            main,
            text="요리 준비하기",
            command=self.on_begin_game,
            width=20,
            height=2,
            bg="#d58e3c",
            fg="#1f160f",
            font=("Malgun Gothic", 12, "bold"),
            relief=tk.RAISED,
        )
        self.start_button.pack_forget()

        self.kitchen_layer = tk.Frame(main, bg="#f4efe7")
        self.kitchen_layer.pack(fill=tk.BOTH, expand=True)

        workspace = tk.Frame(self.kitchen_layer, bg="#f4efe7")
        workspace.pack(fill=tk.BOTH, expand=True)
        workspace.grid_columnconfigure(0, minsize=300, weight=0)
        workspace.grid_columnconfigure(1, minsize=520, weight=1)
        workspace.grid_columnconfigure(2, minsize=220, weight=0)
        workspace.grid_rowconfigure(0, weight=1)

        left_stack = tk.Frame(workspace, bg="#f4efe7", width=300)
        left_stack.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 8))
        left_stack.grid_propagate(False)
        left_stack.grid_rowconfigure(0, weight=3, minsize=210)
        left_stack.grid_rowconfigure(1, weight=2, minsize=180)
        left_stack.grid_columnconfigure(0, weight=1)

        recipe_list_frame = tk.Frame(left_stack, bg="#fbf6ee", bd=2, relief=tk.RIDGE, padx=10, pady=10)
        recipe_list_frame.grid(row=0, column=0, sticky=tk.NSEW)

        tk.Label(recipe_list_frame, text="레시피 목록", font=("Malgun Gothic", 12, "bold"), bg="#fbf6ee").pack(anchor="w")
        search_row = tk.Frame(recipe_list_frame, bg="#fbf6ee")
        search_row.pack(fill=tk.X, pady=(6, 0))
        self.recipe_search_entry = tk.Entry(search_row, font=("Malgun Gothic", 10))
        self.recipe_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.recipe_search_entry.bind("<Return>", self.on_search_recipe)
        tk.Button(
            search_row, text="검색", command=self.on_search_recipe, width=6,
            bg="#e7c78d", font=("Malgun Gothic", 9, "bold"),
        ).pack(side=tk.LEFT, padx=(5, 0))
        tk.Button(
            search_row, text="전체", command=self.on_show_all_recipes, width=5,
            bg="#e8dfd1", font=("Malgun Gothic", 9),
        ).pack(side=tk.LEFT, padx=(4, 0))
        list_frame = tk.Frame(recipe_list_frame, bg="#fbf6ee")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.recipe_listbox = tk.Listbox(
            list_frame, height=6, width=28, font=("Malgun Gothic", 10),
            activestyle="dotbox", exportselection=False,
        )
        self.recipe_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        recipe_scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.recipe_listbox.yview)
        recipe_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.recipe_listbox.configure(yscrollcommand=recipe_scrollbar.set)
        self.recipe_listbox.bind("<<ListboxSelect>>", self.on_recipe_selected)

        guide_frame = tk.Frame(left_stack, bg="#fbf6ee", bd=2, relief=tk.RIDGE, padx=16, pady=10)
        guide_frame.grid(row=1, column=0, sticky=tk.NSEW, pady=(8, 0))

        tk.Label(guide_frame, text="요리 가이드", font=("Malgun Gothic", 12, "bold"), bg="#fbf6ee").pack(anchor="w")
        guide_body = tk.Frame(guide_frame, bg="#fbf6ee")
        guide_body.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.guide_text = tk.Text(
            guide_body, height=8, width=36, wrap=tk.WORD,
            font=("Malgun Gothic", 9), state=tk.DISABLED,
        )
        self.guide_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        guide_scrollbar = tk.Scrollbar(guide_body, orient=tk.VERTICAL, command=self.guide_text.yview)
        guide_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.guide_text.configure(yscrollcommand=guide_scrollbar.set)

        cooking_wrap = tk.Frame(workspace, bg="#f4efe7")
        cooking_wrap.grid(row=0, column=1, sticky=tk.NSEW, padx=4)

        center = tk.Frame(cooking_wrap, bg="#fbf6ee", bd=2, relief=tk.RIDGE, padx=18, pady=18)
        center.pack(fill=tk.BOTH, expand=True)

        tk.Label(center, text="조리 공간", font=("Malgun Gothic", 12, "bold"), bg="#fbf6ee").pack(anchor="w")

        tool_bar = tk.Frame(center, bg="#fbf6ee")
        tool_bar.pack(fill=tk.X, pady=(8, 10))

        self.tool_buttons: Dict[str, tk.Button] = {}
        for tool_name in ["팬", "냄비", "칼", "도마"]:
            btn = tk.Button(tool_bar, text=tool_name, command=lambda name=tool_name: self.select_tool(name),
                            width=10, height=2, bg="#d9d0c1" if tool_name != self.selected_tool else "#d19b4c",
                            fg="#261a12", font=("Malgun Gothic", 10, "bold"), relief=tk.RAISED)
            btn.pack(side=tk.LEFT, padx=6)
            self.tool_buttons[tool_name] = btn

        self.cooking_area = tk.Frame(center, bg="#efe5d3", bd=2, relief=tk.SUNKEN, padx=18, pady=18)
        self.cooking_area.pack(fill=tk.BOTH, expand=True)

        self.tool_labels: Dict[str, tk.Label] = {}
        for idx, tool_name in enumerate(["팬", "냄비"]):
            frame = tk.Frame(self.cooking_area, bg="#efe5d3", bd=1, relief=tk.RAISED, padx=16, pady=16)
            frame.grid(row=0, column=idx, padx=18, pady=10, sticky=tk.NSEW)
            label = tk.Label(frame, text=f"{tool_name}\n비어 있음", font=("Malgun Gothic", 11, "bold"), bg="#dfe9c8",
                             fg="#2d2b2a", justify=tk.CENTER, width=14, height=6)
            label.pack(fill=tk.BOTH, expand=True)
            self.tool_labels[tool_name] = label

        self.knife_label = tk.Label(self.cooking_area, text="칼\n준비 완료", font=("Malgun Gothic", 11, "bold"),
                                    bg="#e6d7b0", fg="#2d2b2a", justify=tk.CENTER, width=12, height=4)
        self.knife_label.grid(row=1, column=0, padx=18, pady=(0, 10), sticky=tk.EW)

        self.board_label = tk.Label(self.cooking_area, text="도마\n재료 손질", font=("Malgun Gothic", 11, "bold"),
                                    bg="#cfdfe7", fg="#2d2b2a", justify=tk.CENTER, width=12, height=4)
        self.board_label.grid(row=1, column=1, padx=18, pady=(0, 10), sticky=tk.EW)

        for i in range(2):
            self.cooking_area.grid_columnconfigure(i, weight=1)

        self.cooking_scene = tk.Canvas(center, bg="#eaf3e4", height=330, width=540, highlightthickness=0)
        self.cooking_scene.pack_forget()
        self.cooking_scene.bind("<ButtonPress-1>", self.on_scene_press)
        self.cooking_scene.bind("<B1-Motion>", self.on_scene_drag)
        self.cooking_scene.bind("<ButtonRelease-1>", self.on_scene_release)

        self.scene_ingredient_items: List[int] = []
        self.scene_ready = False

        self.game_controls = tk.Frame(center, bg="#fbf6ee", padx=8, pady=8)
        self.game_controls.pack_forget()
        game_hud = tk.Frame(self.game_controls, bg="#3b3028", padx=10, pady=8)
        game_hud.pack(fill=tk.X, pady=(0, 8))
        self.timer_var = tk.StringVar(value="남은 시간 03:00")
        self.heat_var = tk.StringVar(value="불 세기: 중불")
        self._ui_string_vars.extend((self.timer_var, self.heat_var))
        tk.Label(game_hud, textvariable=self.timer_var, font=("Malgun Gothic", 12, "bold"),
                 bg="#3b3028", fg="#fff1d2").pack(side=tk.LEFT)
        tk.Label(game_hud, textvariable=self.heat_var, font=("Malgun Gothic", 11, "bold"),
                 bg="#3b3028", fg="#ffd18a").pack(side=tk.RIGHT)

        heat_controls = tk.Frame(self.game_controls, bg="#fbf6ee")
        heat_controls.pack(fill=tk.X, pady=(0, 6))
        tk.Label(heat_controls, text="화력 조절", font=("Malgun Gothic", 10, "bold"),
                 bg="#fbf6ee").pack(side=tk.LEFT, padx=(0, 8))
        self.heat_buttons: Dict[int, tk.Button] = {}
        for level, label in ((1, "약불"), (2, "중불"), (3, "강불")):
            button = tk.Button(
                heat_controls,
                text=label,
                command=lambda value=level: self.set_heat(value),
                width=8,
                bg="#d19b4c" if level == self.heat_level else "#e8dfd1",
                font=("Malgun Gothic", 9, "bold"),
            )
            button.pack(side=tk.LEFT, padx=3)
            self.heat_buttons[level] = button

        tk.Label(self.game_controls, text="재료를 눌러 냄비에 넣으세요",
                 font=("Malgun Gothic", 10, "bold"), bg="#fbf6ee").pack(anchor="w")
        self.game_ingredients = tk.Frame(self.game_controls, bg="#fbf6ee")
        self.game_ingredients.pack(fill=tk.X, pady=(4, 6))
        self.game_ingredient_buttons: Dict[str, tk.Button] = {}

        right = tk.Frame(workspace, bg="#fbf6ee", bd=2, relief=tk.RIDGE, width=220, padx=10, pady=12)
        right.grid(row=0, column=2, sticky=tk.NSEW, padx=(8, 0))
        right.grid_propagate(False)

        tk.Label(right, text="냉장고", font=("Malgun Gothic", 12, "bold"), bg="#fbf6ee").pack(anchor="w")
        self.fridge_listbox = tk.Listbox(right, height=18, width=28, font=("Malgun Gothic", 10), activestyle="dotbox")
        self.fridge_listbox.pack(fill=tk.BOTH, expand=True, pady=(8, 6))
        self.fridge_listbox.bind("<<ListboxSelect>>", self.on_fridge_selected)

        tk.Label(right, text="재료 직접 입력", font=("Malgun Gothic", 10, "bold"),
                 bg="#fbf6ee").pack(anchor="w", pady=(4, 2))
        self.ingredient_entry = tk.Entry(right, font=("Malgun Gothic", 10))
        self.ingredient_entry.pack(fill=tk.X, pady=(0, 5))
        self.ingredient_entry.bind("<Return>", self.on_add_ingredient)
        quantity_row = tk.Frame(right, bg="#fbf6ee")
        quantity_row.pack(fill=tk.X, pady=(0, 5))
        tk.Label(quantity_row, text="개수", bg="#fbf6ee", font=("Malgun Gothic", 9)).pack(side=tk.LEFT)
        self.ingredient_quantity_entry = tk.Entry(quantity_row, width=7, font=("Malgun Gothic", 10))
        self.ingredient_quantity_entry.insert(0, "1")
        self.ingredient_quantity_entry.pack(side=tk.LEFT, padx=(6, 0))
        self.ingredient_quantity_entry.bind("<Return>", self.on_add_ingredient)

        self.fridge_action = tk.Button(right, text="선택 재료를 도구에 넣기", command=self.on_add_selected_to_tool,
                                      bg="#d89b4a", fg="#1d160f", font=("Malgun Gothic", 10, "bold"), relief=tk.RAISED)
        self.fridge_action.pack(fill=tk.X, pady=(0, 6))

        self.fridge_add_button = tk.Button(right, text="냉장고에 저장", command=self.on_add_ingredient,
                                           bg="#e7c78d", fg="#1d160f", font=("Malgun Gothic", 10, "bold"), relief=tk.RAISED)
        self.fridge_add_button.pack(fill=tk.X)

        self.knife_item = self.cooking_scene.create_rectangle(0, 0, 0, 0, fill="#b7bcc4", outline="#4d4d4d", width=3, tags=("knife", "draggable"))
        self.knife_text_item = self.cooking_scene.create_text(0, 0, text="칼", font=("Malgun Gothic", 12, "bold"), fill="#111111", tags=("knife", "draggable"))

        bottom = tk.Frame(main, bg="#f4efe7")
        bottom.pack(fill=tk.X, pady=(12, 0))

        bottom_panel = tk.Frame(bottom, bg="#fbf6ee", bd=2, relief=tk.RIDGE, padx=12, pady=10)
        bottom_panel.pack(fill=tk.BOTH, expand=True)

        tk.Label(bottom_panel, text="식재료 데이터 / 알림", font=("Malgun Gothic", 12, "bold"), bg="#fbf6ee").pack(anchor="w")
        self.status_var = tk.StringVar(value="")
        self._ui_string_vars.append(self.status_var)
        status_bar = tk.Label(bottom_panel, textvariable=self.status_var, anchor="w", justify=tk.LEFT, bg="#2d2d30",
                              fg="#f7f5ee", padx=10, pady=10, font=("Malgun Gothic", 10), wraplength=900)
        status_bar.pack(fill=tk.X, pady=(8, 0))

        button_frame = tk.Frame(main, bg="#f4efe7")
        button_frame.pack(fill=tk.X, pady=(12, 0))

        actions = [
            ("AI 추천", self.on_recommend),
            ("조리 시작", self.on_cook),
            ("다음 단계", self.on_next_step),
            ("평가하기", self.on_evaluate),
        ]
        for text, cmd in actions:
            btn = tk.Button(button_frame, text=text, command=cmd, width=18, height=2, bg="#e4b368", fg="#1d160f",
                            font=("Malgun Gothic", 10, "bold"), relief=tk.RAISED)
            btn.pack(side=tk.LEFT, padx=6)

        language_frame = tk.Frame(main, bg="#f4efe7")
        language_frame.pack(fill=tk.X, pady=(8, 0))
        self.language_var = tk.StringVar(value=self._language_name(self.lang))
        self.language_menu = tk.OptionMenu(
            language_frame,
            self.language_var,
            *LANGUAGE_OPTIONS.keys(),
            command=lambda selected: (
                self._on_language_selected(self.language_var.get()) if selected else None
            ),
        )
        self.language_menu.configure(
            bg="#e8dfd1",
            font=("Malgun Gothic", 9),
            highlightthickness=0,
        )
        self.language_menu.pack(side=tk.RIGHT)
        self.language_label = tk.Label(
            language_frame,
            text="언어 선택",
            bg="#f4efe7",
            font=("Malgun Gothic", 9, "bold"),
        )
        self.language_label.pack(side=tk.RIGHT, padx=(0, 6))

    def _update_page_scrollregion(self, _event=None) -> None:
        self.page_canvas.configure(scrollregion=self.page_canvas.bbox("all"))

    def _resize_page_content(self, event: tk.Event) -> None:
        self.page_canvas.itemconfigure(self.page_window, width=event.width)

    def _on_page_mousewheel(self, event: tk.Event) -> str:
        if event.num == 4:
            direction = -1
        elif event.num == 5:
            direction = 1
        else:
            direction = -1 if event.delta > 0 else 1

        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget is not None and widget is not self:
            if isinstance(widget, (tk.Listbox, tk.Text)):
                first, last = widget.yview()
                can_scroll = first > 0 if direction < 0 else last < 1
                if can_scroll:
                    widget.yview_scroll(direction, "units")
                    return "break"
            widget = widget.master

        if event.delta:
            units = max(1, abs(int(event.delta / 120))) * 3
            self.page_canvas.yview_scroll(direction * units, "units")
        else:
            self.page_canvas.yview_scroll(direction * 3, "units")
        return "break"

    def _language_name(self, language_code: str) -> str:
        return next(
            (name for name, code in LANGUAGE_OPTIONS.items() if code == language_code),
            "한국어",
        )

    def _on_language_selected(self, language_name: str) -> None:
        target_language = LANGUAGE_OPTIONS.get(language_name)
        if target_language is not None:
            self._apply_language(target_language)

    def _current_text_source(self, key: Tuple[Any, ...], current: str) -> str:
        rendered = self._ui_text_rendered.get(key)
        if key not in self._ui_text_sources or (rendered is not None and current != rendered):
            self._ui_text_sources[key] = current
        return self._ui_text_sources[key]

    def _current_sequence_source(
        self, key: Tuple[Any, ...], current: Tuple[str, ...]
    ) -> Tuple[str, ...]:
        rendered = self._ui_sequence_rendered.get(key)
        if key not in self._ui_sequence_sources or (rendered is not None and current != rendered):
            self._ui_sequence_sources[key] = current
        return self._ui_sequence_sources[key]

    def _apply_language(self, target_language: str) -> None:
        text_entries: List[Tuple[Tuple[Any, ...], str, Any]] = []
        sequence_entries: List[Tuple[Tuple[Any, ...], Tuple[str, ...], Any]] = []

        title_key = ("window_title",)
        title_source = self._current_text_source(title_key, self.title())
        text_entries.append((title_key, title_source, self.title))

        for widget in self._walk_widgets(self):
            if widget is self.language_menu:
                continue
            if isinstance(widget, tk.Canvas):
                for item_id in widget.find_all():
                    if widget.type(item_id) == "text":
                        text = widget.itemcget(item_id, "text")
                        if text:
                            key = ("canvas", widget, item_id)
                            source = self._current_text_source(key, text)
                            text_entries.append((
                                key,
                                source,
                                lambda value, canvas=widget, item=item_id: canvas.itemconfigure(
                                    item, {"text": value}
                                ),
                            ))
            elif isinstance(widget, tk.Listbox):
                current = tuple(widget.get(0, tk.END))
                if current:
                    key = ("listbox", widget)
                    source = self._current_sequence_source(key, current)
                    sequence_entries.append((
                        key,
                        source,
                        lambda values, listbox=widget: self._replace_listbox_items(listbox, values),
                    ))
            elif isinstance(widget, tk.Text):
                current_text = widget.get("1.0", "end-1c")
                if current_text:
                    key = ("text", widget)
                    source = self._current_sequence_source(key, (current_text,))
                    sequence_entries.append((
                        key,
                        source,
                        lambda values, text_widget=widget: self._replace_text_widget(text_widget, values[0]),
                    ))
            else:
                try:
                    current_text = widget.cget("text")
                except tk.TclError:
                    continue
                if current_text:
                    key = ("widget", widget)
                    source = self._current_text_source(key, current_text)
                    text_entries.append((
                        key,
                        source,
                        lambda value, text_widget=widget: text_widget.configure({"text": value}),
                    ))

        for variable in self._ui_string_vars:
            if variable is self.timer_var:
                continue
            current_text = variable.get()
            if current_text:
                key = ("variable", str(variable))
                source = self._current_text_source(key, current_text)
                text_entries.append((key, source, variable.set))

        texts_to_translate = [entry[1] for entry in text_entries]
        for _, sequence, _ in sequence_entries:
            texts_to_translate.extend(sequence)
        texts_to_translate.append("남은 시간")

        try:
            translations = self.translator.translate_many(texts_to_translate, target_language)
        except TranslationError as error:
            self.language_var.set(self._language_name(self.lang))
            messagebox.showerror("번역 오류", str(error), parent=self)
            return

        self._ui_translation_applying = True
        try:
            self.lang = target_language
            text_count = len(text_entries)
            for (key, _, apply_text), translated_text in zip(text_entries, translations[:text_count]):
                apply_text(translated_text)
                self._ui_text_rendered[key] = translated_text

            offset = text_count
            for key, source_sequence, apply_sequence in sequence_entries:
                translated_sequence = tuple(translations[offset:offset + len(source_sequence)])
                offset += len(source_sequence)
                apply_sequence(translated_sequence)
                self._ui_sequence_rendered[key] = translated_sequence

            self._update_timer_display()
            self.update_idletasks()
        finally:
            self._ui_translation_applying = False

    def _replace_listbox_items(self, listbox: tk.Listbox, values: Tuple[str, ...]) -> None:
        selection = listbox.curselection()
        listbox.delete(0, tk.END)
        for value in values:
            listbox.insert(tk.END, value)
        for index in selection:
            if index < len(values):
                listbox.selection_set(index)

    def _replace_text_widget(self, widget: tk.Text, value: str) -> None:
        previous_state = widget.cget("state")
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value)
        widget.configure(state=previous_state)

    def _walk_widgets(self, parent: tk.Misc) -> List[tk.Misc]:
        widgets = []
        for child in parent.winfo_children():
            widgets.append(child)
            widgets.extend(self._walk_widgets(child))
        return widgets

    def _queue_ui_translation(self, _event=None) -> None:
        if self.lang == "ko" or self._ui_translation_pending or self._ui_translation_applying:
            return
        self._ui_translation_pending = True
        self.after_idle(self._refresh_ui_translation)

    def _refresh_ui_translation(self) -> None:
        self._ui_translation_pending = False
        if self.lang != "ko":
            self._apply_language(self.lang)

    def refresh_recipe_list(self) -> None:
        self.recipe_listbox.delete(0, tk.END)
        for recipe in self.recipes:
            self.recipe_listbox.insert(tk.END, recipe.name)

    def on_search_recipe(self, _event=None) -> None:
        query = self.recipe_search_entry.get().strip()
        if not query:
            self.status_var.set("찾을 요리 이름이나 키워드를 입력하세요.")
            return
        self._stop_cooking_timer()
        self.cooking_started = False
        self.current_recipe = None
        self.recipes = load_recipes(self.api_key, limit=10, query=query)
        self.refresh_recipe_list()
        self.update_recipe_guide()
        self.update_tool_panel()
        self.switch_cooking_view()
        if not self.recipes:
            self.status_var.set(f"'{query}' 검색 결과가 없습니다. 다른 검색어를 입력해 보세요.")
            return
        if any(recipe.source == "spoonacular" for recipe in self.recipes):
            self.status_var.set(f"'{query}' Spoonacular 검색 결과 {len(self.recipes)}개입니다.")
        else:
            self.status_var.set(f"API 검색 결과가 없어 로컬 레시피에서 '{query}'를 찾았습니다.")

    def on_show_all_recipes(self) -> None:
        self._stop_cooking_timer()
        self.cooking_started = False
        self.current_recipe = None
        self.recipes = self.all_recipes[:]
        self.recipe_search_entry.delete(0, tk.END)
        self.refresh_recipe_list()
        self.update_recipe_guide()
        self.switch_cooking_view()
        self.status_var.set(f"전체 레시피 {len(self.recipes)}개를 표시합니다.")

    def refresh_fridge(self) -> None:
        self.fridge_listbox.delete(0, tk.END)
        for item in self.fridge.list_items():
            self.fridge_listbox.insert(tk.END, item)

    def on_begin_game(self) -> None:
        self.game_opened = True
        self.cooking_started = False
        self.start_button.pack_forget()
        self.kitchen_layer.pack(fill=tk.BOTH, expand=True)
        if self.current_recipe is None and self.recipes:
            self.current_recipe = self.recipes[0]
            self.sim.set_recipe(self.current_recipe)
        if self.current_recipe is None:
            self.status_var.set("레시피를 불러오지 못했습니다. API 키나 네트워크를 확인해 주세요.")
            return
        self.update_recipe_guide()
        self.update_tool_panel()
        self.switch_cooking_view()
        self.status_var.set("요리를 검색하거나 선택한 뒤, 하단의 조리 시작 버튼을 누르세요.")

    def select_tool(self, tool_name: str) -> None:
        self.selected_tool = tool_name
        for name, button in self.tool_buttons.items():
            button.configure(bg="#d9d0c1" if name != tool_name else "#d19b4c")
        self.status_var.set(f"{tool_name} 조리 도구를 선택했습니다. 재료를 넣어 조리하세요.")

    def refresh_cooking_scene(self) -> None:
        if self.current_recipe is None:
            return

        self.cooking_scene.delete("all")
        self.scene_ingredient_items = []
        self.scene_ingredient_by_tag.clear()
        self.scene_cut_indices.clear()

        self.cooking_scene.create_rectangle(0, 0, 540, 330, fill="#e9dcc7", outline="")
        self.cooking_scene.create_rectangle(16, 14, 524, 58, fill="#5b4030", outline="#3d2c21", width=2)
        self.cooking_scene.create_text(
            270, 36, text=self.current_recipe.name, font=("Malgun Gothic", 16, "bold"),
            fill="#fff1d2",
        )

        pan_color = {1: "#c5d5dc", 2: "#d9d3bb", 3: "#edb58c"}[self.heat_level]
        self.cooking_scene.create_rectangle(
            24, 76, 250, 286, fill="#d5bb94", outline="#8a623d", width=4,
            tags=("draggable", "drag:board"),
        )
        self.cooking_scene.create_text(
            137, 94, text="재료 준비대", font=("Malgun Gothic", 12, "bold"),
            fill="#5b3822", tags=("draggable", "drag:board"),
        )

        tool_tags = ("draggable", "drag:pan")
        self.cooking_scene.create_rectangle(470, 188, 526, 207, fill="#55565a", outline="#303136", width=3, tags=tool_tags)
        self.cooking_scene.create_oval(292, 116, 500, 280, fill="#57585d", outline="#303136", width=5, tags=tool_tags)
        self.cooking_scene.create_oval(
            308, 130, 484, 266, fill=pan_color, outline="#a4a5a8", width=3,
            tags=(*tool_tags, "pan_interior"),
        )
        self.cooking_scene.create_text(
            396, 296, text="조리 냄비", font=("Malgun Gothic", 12, "bold"),
            fill="#3a312a", tags=tool_tags,
        )
        pan_items = self.sim.tools.get("팬", [])
        self.cooking_scene.create_text(
            396, 198, text="\n".join(pan_items[-5:]) if pan_items else "재료를 넣어 주세요",
            font=("Malgun Gothic", 9, "bold"), fill="#303136", width=155, justify=tk.CENTER,
            tags=(*tool_tags, "pan_contents"),
        )

        step_text = (
            self.current_recipe.steps[self.current_step_index]
            if self.current_step_index < len(self.current_recipe.steps)
            else "모든 조리 단계가 끝났습니다!"
        )
        self.cooking_scene.create_rectangle(16, 298, 524, 326, fill="#fff8eb", outline="#9f7953", width=2)
        self.cooking_scene.create_text(
            270, 312, text=f"{self.current_step_index + 1}/{len(self.current_recipe.steps)}  {step_text}",
            font=("Malgun Gothic", 8, "bold"), fill="#4a3728", width=490,
            tags=("step_instruction",),
        )

        items = self.current_recipe.ingredients[:8]
        for idx, ingredient in enumerate(items):
            x = 38 + (idx % 2) * 104
            y = 116 + (idx // 2) * 40
            object_tag = f"drag:ingredient:{idx}"
            tags = ("ingredient", "draggable", object_tag)
            blob = self.cooking_scene.create_oval(
                x, y, x + 96, y + 30, fill="#f8d9a5", outline="#8f5d2c",
                width=2, tags=tags,
            )
            self.cooking_scene.create_text(
                x + 48, y + 15, text=ingredient[:12], font=("Malgun Gothic", 7, "bold"),
                tags=tags,
            )
            self.scene_ingredient_items.append(blob)
            self.scene_ingredient_by_tag[object_tag] = ingredient

        self.cooking_scene.create_rectangle(
            230, 238, 244, 276, fill="#a4aeb7", outline="#444b52", width=2,
            tags=("draggable", "drag:knife"),
        )
        self.cooking_scene.create_rectangle(
            226, 268, 248, 284, fill="#744b31", outline="#3e2c20", width=2,
            tags=("draggable", "drag:knife"),
        )

    def switch_cooking_view(self) -> None:
        if self.cooking_started:
            self.cooking_area.pack_forget()
            self.refresh_cooking_scene()
            self.cooking_scene.pack(fill=tk.BOTH, expand=True)
            self.game_controls.pack(fill=tk.X, pady=(8, 0))
        else:
            self.cooking_scene.pack_forget()
            self.game_controls.pack_forget()
            self.cooking_area.pack(fill=tk.BOTH, expand=True)

    def _refresh_cook_controls(self) -> None:
        for button in self.game_ingredient_buttons.values():
            button.destroy()
        self.game_ingredient_buttons.clear()
        if self.current_recipe is None:
            return

        added = set(self.sim.tools["팬"])
        for index, ingredient in enumerate(self.current_recipe.ingredients):
            button = tk.Button(
                self.game_ingredients,
                text=ingredient,
                command=lambda item=ingredient: self.add_game_ingredient(item),
                state=tk.DISABLED if ingredient in added else tk.NORMAL,
                bg="#e8dfd1" if ingredient in added else "#f8d9a5",
                font=("Malgun Gothic", 9),
                wraplength=110,
            )
            button.grid(row=index // 4, column=index % 4, padx=3, pady=3, sticky=tk.EW)
            self.game_ingredient_buttons[ingredient] = button
        for column in range(4):
            self.game_ingredients.grid_columnconfigure(column, weight=1)

    def _update_timer_display(self) -> None:
        minutes, seconds = divmod(max(0, self.remaining_seconds), 60)
        prefix = self.translator.cached_translation("남은 시간", self.lang)
        self.timer_var.set(f"{prefix} {minutes:02d}:{seconds:02d}")

    def _stop_cooking_timer(self) -> None:
        if self.timer_after_id is not None:
            self.after_cancel(self.timer_after_id)
            self.timer_after_id = None

    def _tick_cooking_timer(self) -> None:
        self.timer_after_id = None
        if not self.cooking_started:
            return
        self.remaining_seconds = max(0, self.remaining_seconds - 1)
        self._update_timer_display()
        if self.remaining_seconds == 0:
            self.status_var.set("시간이 끝났습니다. 현재까지 진행한 조리 단계로 평가할 수 있습니다.")
            self._queue_ui_translation()
            return
        self.timer_after_id = self.after(1000, self._tick_cooking_timer)

    def set_heat(self, level: int) -> None:
        if level not in (1, 2, 3):
            return
        if self.cooking_started and self.remaining_seconds <= 0:
            self.status_var.set("시간이 끝나 화력을 조절할 수 없습니다.")
            return
        self.heat_level = level
        heat_names = {1: "약불", 2: "중불", 3: "강불"}
        self.heat_var.set(f"불 세기: {heat_names[level]}")
        for button_level, button in self.heat_buttons.items():
            button.configure(bg="#d19b4c" if button_level == level else "#e8dfd1")
        if self.cooking_scene.find_withtag("pan_interior"):
            pan_color = {1: "#c5d5dc", 2: "#d9d3bb", 3: "#edb58c"}[level]
            self.cooking_scene.itemconfigure("pan_interior", fill=pan_color)
        self.status_var.set(f"화력을 {heat_names[level]}로 조절했습니다.")

    def add_game_ingredient(self, ingredient: str) -> None:
        if not self.cooking_started or self.current_recipe is None:
            return
        if self.remaining_seconds <= 0:
            self.status_var.set("시간이 끝나 재료를 추가할 수 없습니다.")
            return
        if ingredient not in self.current_recipe.ingredients:
            return
        if ingredient in self.sim.tools["팬"]:
            self.status_var.set(f"{ingredient}은(는) 이미 냄비에 넣었습니다.")
            return
        self.sim.tools["팬"].append(ingredient)
        self.update_tool_panel()
        self._refresh_cook_controls()
        pan_items = self.sim.tools["팬"]
        self.cooking_scene.itemconfigure(
            "pan_contents",
            text="\n".join(pan_items[-5:]) if pan_items else "재료를 넣어 주세요",
        )
        self.status_var.set(f"{ingredient}을(를) 냄비에 넣었습니다.")

    def on_scene_press(self, event: tk.Event) -> None:
        if not self.cooking_started or self.remaining_seconds <= 0:
            return
        overlapping = self.cooking_scene.find_overlapping(event.x, event.y, event.x, event.y)
        for item_id in reversed(overlapping):
            tags = self.cooking_scene.gettags(item_id)
            drag_tag = next((tag for tag in tags if tag.startswith("drag:")), None)
            if drag_tag is not None:
                self.dragged_tag = drag_tag
                self.drag_anchor = (event.x, event.y)
                self.cooking_scene.tag_raise(drag_tag)
                self.knife_dragging = True
                return

    def on_scene_drag(self, event: tk.Event) -> None:
        if not self.knife_dragging or self.dragged_tag is None:
            return
        dx = event.x - self.drag_anchor[0]
        dy = event.y - self.drag_anchor[1]
        bounds = self.cooking_scene.bbox(self.dragged_tag)
        if bounds is None:
            return
        canvas_width = max(self.cooking_scene.winfo_width(), int(self.cooking_scene.cget("width")))
        canvas_height = max(self.cooking_scene.winfo_height(), int(self.cooking_scene.cget("height")))
        dx = max(-bounds[0], min(dx, canvas_width - bounds[2]))
        dy = max(-bounds[1], min(dy, canvas_height - bounds[3]))
        self.cooking_scene.move(self.dragged_tag, dx, dy)
        self.drag_anchor = (event.x, event.y)
        if self.dragged_tag == "drag:knife":
            self._cut_ingredient_at_knife()

    def on_scene_release(self, _event: tk.Event) -> None:
        dragged_tag = self.dragged_tag
        if dragged_tag in self.scene_ingredient_by_tag and self._ingredient_over_pan(dragged_tag):
            ingredient = self.scene_ingredient_by_tag[dragged_tag]
            if ingredient not in self.sim.tools["팬"]:
                self.add_game_ingredient(ingredient)
                for ingredient_tag, name in list(self.scene_ingredient_by_tag.items()):
                    if name == ingredient:
                        self.cooking_scene.delete(ingredient_tag)
                        del self.scene_ingredient_by_tag[ingredient_tag]
        elif dragged_tag and dragged_tag.startswith("drag:ingredient:"):
            ingredient = self.scene_ingredient_by_tag.get(dragged_tag)
            if ingredient in self.sim.tools["팬"]:
                self.status_var.set(f"{ingredient}은(는) 이미 냄비에 넣었습니다.")
        self.knife_dragging = False
        self.dragged_tag = None

    def _ingredient_over_pan(self, ingredient_tag: str) -> bool:
        bounds = self.cooking_scene.bbox(ingredient_tag)
        if bounds is None:
            return False
        return any(
            "pan_interior" in self.cooking_scene.gettags(item_id)
            for item_id in self.cooking_scene.find_overlapping(*bounds)
        )

    def _cut_ingredient_at_knife(self) -> None:
        knife_bounds = self.cooking_scene.bbox("drag:knife")
        if knife_bounds is None:
            return
        for item_id in self.cooking_scene.find_overlapping(*knife_bounds):
            for tag in self.cooking_scene.gettags(item_id):
                if tag not in self.scene_ingredient_by_tag:
                    continue
                try:
                    ingredient_index = int(tag.split(":")[2])
                except (IndexError, ValueError):
                    continue
                if ingredient_index not in self.scene_cut_indices:
                    self._split_scene_ingredient(tag, ingredient_index)
                    return

    def _split_scene_ingredient(self, ingredient_tag: str, ingredient_index: int) -> None:
        bounds = self.cooking_scene.bbox(ingredient_tag)
        ingredient = self.scene_ingredient_by_tag.pop(ingredient_tag, None)
        if bounds is None or ingredient is None:
            return

        self.cooking_scene.delete(ingredient_tag)
        self.scene_cut_indices.add(ingredient_index)
        left, top, right, bottom = bounds
        piece_width = (right - left - 4) / 2
        for side, piece_left in (("left", left), ("right", left + piece_width + 4)):
            piece_tag = f"drag:ingredient:{ingredient_index}:{side}"
            tags = ("ingredient", "ingredient_piece", "draggable", piece_tag)
            piece_right = piece_left + piece_width
            self.cooking_scene.create_oval(
                piece_left, top, piece_right, bottom,
                fill="#f3c987", outline="#8f5d2c", width=2, tags=tags,
            )
            self.cooking_scene.create_text(
                (piece_left + piece_right) / 2, (top + bottom) / 2,
                text=f"{ingredient[:6]} ½", font=("Malgun Gothic", 7, "bold"),
                tags=tags,
            )
            self.scene_ingredient_by_tag[piece_tag] = ingredient
        self.status_var.set(f"{ingredient}을(를) 반으로 잘랐습니다.")

    def update_tool_panel(self) -> None:
        for tool_name, label in self.tool_labels.items():
            items = self.sim.tools.get(tool_name, [])
            label.configure(text=f"{tool_name}\n{', '.join(items) if items else '비어 있음'}")

    def update_recipe_guide(self) -> None:
        self.guide_text.configure(state=tk.NORMAL)
        self.guide_text.delete("1.0", tk.END)

        if self.current_recipe is None:
            self.guide_text.insert(tk.END, "요리를 선택하면 가이드가 표시됩니다.\n\n왼쪽 목록에서 요리를 고른 뒤 조리 시작을 눌러 직접 요리를 진행해 보세요.")
        else:
            recipe = self.current_recipe
            self.guide_text.insert(tk.END, f"요리명: {recipe.name}\n")
            self.guide_text.insert(tk.END, f"종류: {recipe.cuisine}\n")
            self.guide_text.insert(tk.END, f"설명: {recipe.description}\n\n")

            if self.cooking_started:
                step_number = min(self.current_step_index + 1, len(recipe.steps))
                step_text = recipe.steps[self.current_step_index] if self.current_step_index < len(recipe.steps) else "조리 완료"
                self.guide_text.insert(tk.END, f"현재 단계: {step_number}/{len(recipe.steps)}\n")
                self.guide_text.insert(tk.END, f"조리 순서: {step_text}\n\n")

            self.guide_text.insert(tk.END, f"필수 재료: {', '.join(recipe.ingredients)}\n")
            self.guide_text.insert(tk.END, "Tip: 냉장고에서 재료를 선택한 뒤, 팬이나 냄비를 눌러 조리 공간에 넣어 주세요.")

        self.guide_text.configure(state=tk.DISABLED)

    def on_recipe_selected(self, _event=None) -> None:
        selection = self.recipe_listbox.curselection()
        if not selection:
            return
        self._stop_cooking_timer()
        recipe = self.recipes[selection[0]]
        for items in self.sim.tools.values():
            items.clear()
        self.current_recipe = recipe
        self.sim.set_recipe(recipe)
        self.cooking_started = False
        self.current_step_index = 0
        self.remaining_seconds = self.time_limit
        self._update_timer_display()
        self.update_recipe_guide()
        self.update_tool_panel()
        self.switch_cooking_view()
        self.status_var.set(f"'{recipe.name}'을(를) 선택했습니다. 조리 시작을 누르면 직접 조리할 수 있습니다.")

    def on_fridge_selected(self, _event=None) -> None:
        selection = self.fridge_listbox.curselection()
        if not selection:
            return
        raw = self.fridge_listbox.get(selection[0])
        name = raw.split(":")[0].strip()
        self.selected_ingredient = name
        self.status_var.set(f"재료 선택: {name}. 조리 도구를 클릭해 넣어 주세요.")

    def on_add_selected_to_tool(self) -> None:
        if self.selected_ingredient is None:
            self.status_var.set("냉장고에서 먼저 재료를 선택하세요.")
            return
        result = self.sim.put_in_tool(self.selected_tool, self.selected_ingredient)
        self.update_tool_panel()
        self.status_var.set(result)

    def on_add_ingredient(self, _event=None) -> None:
        name = self.ingredient_entry.get().strip()
        if not name:
            self.status_var.set("저장할 재료 이름을 입력하세요.")
            return
        try:
            quantity = int(self.ingredient_quantity_entry.get())
        except ValueError:
            self.status_var.set("재료 개수는 1 이상의 정수로 입력하세요.")
            return
        if quantity < 1:
            self.status_var.set("재료 개수는 1 이상이어야 합니다.")
            return
        if name not in INGREDIENT_CATALOG:
            INGREDIENT_CATALOG[name] = Ingredient(name, "기타")
        msg = self.fridge.add_item(name, quantity)
        self.ingredient_entry.delete(0, tk.END)
        self.ingredient_quantity_entry.delete(0, tk.END)
        self.ingredient_quantity_entry.insert(0, "1")
        self.refresh_fridge()
        self.status_var.set(msg)

    def on_cook(self) -> None:
        if self.current_recipe is None:
            self.status_var.set("먼저 요리를 선택하세요.")
            return
        if self.cooking_started:
            self.status_var.set("이미 조리 중입니다. 재료를 넣고 조리 단계를 진행하세요.")
            return

        for items in self.sim.tools.values():
            items.clear()
        result = self.sim.simulate_cooking(self.current_recipe)
        self.cooking_started = True
        self.current_step_index = 0
        self.remaining_seconds = self.time_limit
        self.heat_level = 2
        self._update_timer_display()
        self.heat_var.set("불 세기: 중불")
        self.game_opened = True
        self.start_button.pack_forget()
        self.kitchen_layer.pack(fill=tk.BOTH, expand=True)
        self.set_heat(self.heat_level)
        self._refresh_cook_controls()
        self.update_recipe_guide()
        self.update_tool_panel()
        self.switch_cooking_view()
        self.timer_after_id = self.after(1000, self._tick_cooking_timer)
        self.status_var.set(f"{result['message']} 재료를 누르고 불을 조절하며 조리 단계를 진행하세요.")

    def on_next_step(self) -> None:
        if self.current_recipe is None:
            self.status_var.set("조리할 요리를 먼저 선택하세요.")
            return
        if not self.cooking_started:
            self.status_var.set("조리 시작을 먼저 눌러 조리 모드를 활성화하세요.")
            return
        if self.remaining_seconds <= 0:
            self.status_var.set("시간이 끝났습니다. 평가하기를 눌러 결과를 확인하세요.")
            return

        if self.current_step_index < len(self.current_recipe.steps):
            self.current_step_index += 1
            step_text = (
                self.current_recipe.steps[self.current_step_index]
                if self.current_step_index < len(self.current_recipe.steps)
                else "모든 조리 단계가 끝났습니다!"
            )
            self.cooking_scene.itemconfigure(
                "step_instruction",
                text=f"{self.current_step_index + 1}/{len(self.current_recipe.steps)}  {step_text}",
            )
            self.update_recipe_guide()
            if self.current_step_index >= len(self.current_recipe.steps):
                self._stop_cooking_timer()
                self.status_var.set(f"{self.current_recipe.name} 요리 완성! 이제 평가를 해보세요.")
            else:
                self.status_var.set(f"다음 단계 진행: {self.current_recipe.steps[self.current_step_index - 1]}")
        else:
            self.status_var.set(f"{self.current_recipe.name} 조리는 이미 완료되었습니다.")

    def on_recommend(self) -> None:
        recommendations = self.assistant.recommend(
            self.fridge,
            self.all_recipes,
            preferred_taste="balanced",
            api_key=self.api_key,
            limit=RECOMMENDATION_LIMIT,
        )
        if not recommendations:
            self.status_var.set("추천할 요리를 찾지 못했습니다.")
            return
        self._stop_cooking_timer()
        for items in self.sim.tools.values():
            items.clear()
        self.current_recipe = None
        self.cooking_started = False
        self.current_step_index = 0
        self.remaining_seconds = self.time_limit
        self._update_timer_display()
        self.recipes = recommendations
        self.refresh_recipe_list()
        self.update_recipe_guide()
        self.update_tool_panel()
        self.switch_cooking_view()
        if self.assistant.used_popular_fallback:
            self.status_var.set("만들 수 있는 요리가 없어 인기 요리 5개를 추천했습니다. 목록에서 선택하세요.")
        else:
            self.status_var.set(f"냉장고 재료로 만들 수 있는 요리 {len(recommendations)}개를 추천했습니다. 목록에서 선택하세요.")

    def on_evaluate(self) -> None:
        if self.current_recipe is None:
            self.status_var.set("평가할 요리를 먼저 선택하세요.")
            return
        if not self.cooking_started and self.current_step_index == 0:
            self.status_var.set("조리 시작 후 평가할 수 있습니다.")
            return

        selected_ingredients = []
        for items in self.sim.tools.values():
            selected_ingredients.extend(items)

        completed_steps = self.current_recipe.steps[:self.current_step_index]
        evaluation = self.evaluator.evaluate(
            self.current_recipe,
            selected_ingredients,
            completed_steps,
            taste_profile="balanced",
        )
        time_bonus = (
            min(10, max(0, self.remaining_seconds // 15))
            if self.current_step_index >= len(self.current_recipe.steps)
            else 0
        )
        evaluation_score = evaluation["score"]
        if not isinstance(evaluation_score, int):
            raise TypeError("요리 평가 점수가 정수가 아닙니다.")
        final_score = min(100, evaluation_score + time_bonus)
        message = (
            f"{self.current_recipe.name}\n"
            f"점수: {final_score}점 (시간 보너스 +{time_bonus})\n"
            f"맛: {evaluation['taste']}\n"
            f"완성도: {evaluation['completion']}\n"
            f"피드백: {evaluation['feedback']}"
        )
        self._stop_cooking_timer()
        self.cooking_started = False
        messagebox.showinfo("요리 평가", message)
        self.status_var.set(f"평가 완료: {self.current_recipe.name} ({final_score}점)")
        self.switch_cooking_view()


# ---------------------------------------------------------------------------
# 12. 실행용 메인 로직
# ---------------------------------------------------------------------------
RECIPES: List[Recipe] = []


def demo_run(lang: str = "ko", api_key: str = DEFAULT_API_KEY) -> None:
    """바로 실행해 볼 수 있는 데모 시연."""
    global RECIPES
    RECIPES = load_recipes(api_key, limit=10)

    fridge = Fridge()
    sim = CookingSimulation()
    assistant = AIKitchenAssistant()
    evaluator = RecipeEvaluator()
    ui = KitchenUI(lang)

    ui.print_header("데모 모드")
    if any(recipe.source == "spoonacular" for recipe in RECIPES):
        print(f"불러온 레시피 수: {len(RECIPES)}개")
        print(f"출처: {RECIPE_SOURCE} ({RECIPE_SOURCE_URL})")
    recommendations = assistant.recommend(fridge, RECIPES, api_key=api_key)
    recommended: Optional[Recipe] = None
    if recommendations:
        print("AI 추천:")
        for index, recipe in enumerate(recommendations, start=1):
            print(f"{index}. {recipe.name}")
        recommended = recommendations[0]
        sim.set_recipe(recommended)
        ui.print_recipe_panel(recommended)
    ui.print_cooking_area(sim)
    ui.print_fridge(fridge)

    if recommended is not None:
        for ing in recommended.ingredients[:3]:
            sim.tools["팬"].append(ing)

        evaluation = evaluator.evaluate(
            recommended,
            sim.tools["팬"],
            recommended.steps,
            taste_profile="balanced",
        )
        print(f"\nAI 추천 요리: {recommended.name}")
        print(f"점수: {evaluation['score']}점")
        print(f"맛: {evaluation['taste']}")
        print(f"완성도: {evaluation['completion']}")
        print(f"피드백: {evaluation['feedback']}")

    ui.print_bottom_panel(_("thanks", lang))


def interactive_loop(lang: str = "ko", api_key: str = DEFAULT_API_KEY) -> None:
    """사용자가 메뉴를 선택해 조작하는 인터랙티브 로직."""
    global RECIPES
    RECIPES = load_recipes(api_key, limit=10)

    fridge = Fridge()
    sim = CookingSimulation()
    assistant = AIKitchenAssistant()
    evaluator = RecipeEvaluator()
    ui = KitchenUI(lang)

    if any(recipe.source == "spoonacular" for recipe in RECIPES):
        print(_("api_loaded", lang))
    else:
        print(_("api_fallback", lang))

    current_recipe: Optional[Recipe] = None

    while True:
        ui.print_header()
        if current_recipe is not None:
            ui.print_recipe_panel(current_recipe)
        ui.print_cooking_area(sim)
        ui.print_fridge(fridge)
        ui.print_menu()

        try:
            choice = input("선택: ")
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            break

        if choice == "1":
            print("\n[ 요리 목록 ]")
            for idx, recipe in enumerate(RECIPES, start=1):
                print(f"{idx}. {recipe.name}")
            recipe_idx = input("자세히 볼 요리 번호를 입력하세요 (Enter: 취소): ").strip()
            if recipe_idx:
                try:
                    idx = int(recipe_idx) - 1
                    current_recipe = RECIPES[idx]
                    sim.set_recipe(current_recipe)
                    ui.print_bottom_panel(f"'{current_recipe.name}'이(가) 선택되었습니다.")
                    # 상세 조리법은 요리를 선택한 뒤, 다음 루프에서 recipe_panel에 표시됩니다.
                except (ValueError, IndexError):
                    ui.print_bottom_panel(_("invalid", lang))

        elif choice == "2":
            recommendations = assistant.recommend(
                fridge,
                RECIPES,
                preferred_taste="balanced",
                api_key=api_key,
            )
            print("\n[ AI 요리 추천 ]")
            for idx, recipe in enumerate(recommendations, start=1):
                print(f"{idx}. {recipe.name}")
            if assistant.used_popular_fallback:
                print("만들 수 있는 요리가 없어 인기 요리를 추천했습니다.")
            if recommendations:
                recipe_choice = input("선택할 요리 번호 (Enter: 취소): ").strip()
                if recipe_choice:
                    try:
                        current_recipe = recommendations[int(recipe_choice) - 1]
                        sim.set_recipe(current_recipe)
                        ui.print_bottom_panel(f"AI 추천 요리 선택: {current_recipe.name}")
                    except (ValueError, IndexError):
                        ui.print_bottom_panel(_("invalid", lang))

        elif choice == "3":
            ingredient_name = input("추가할 재료 이름을 입력하세요: ").strip()
            if ingredient_name:
                result = fridge.add_item(ingredient_name)
                ui.print_bottom_panel(result)

        elif choice == "4":
            ingredient_name = input("꺼낼 재료 이름을 입력하세요: ").strip()
            if ingredient_name:
                result = fridge.take_item(ingredient_name)
                ui.print_bottom_panel(result)

        elif choice == "5":
            if current_recipe is None:
                ui.print_bottom_panel("먼저 레시피를 선택하세요.")
                continue

            ingredient_name = input("조리 도구에 넣을 재료 이름을 입력하세요: ").strip()
            tool_name = input("도구 이름을 입력하세요 (팬 / 냄비 / 도마 / 그릇): ").strip()
            if ingredient_name:
                result = sim.put_in_tool(tool_name, ingredient_name)
                ui.print_bottom_panel(result)

        elif choice == "6":
            if current_recipe is None:
                ui.print_bottom_panel("먼저 요리를 선택해주세요.")
                continue

            result = sim.simulate_cooking(current_recipe)
            if result["success"]:
                ui.print_bottom_panel(f"{result['message']}\n{result['steps']}")
            else:
                ui.print_bottom_panel(str(result["message"]))

        elif choice == "7":
            if current_recipe is None:
                ui.print_bottom_panel("먼저 요리를 선택하세요.")
                continue

            selected_ingredients = []
            for items in sim.tools.values():
                selected_ingredients.extend(items)

            evaluation = evaluator.evaluate(
                current_recipe,
                selected_ingredients,
                current_recipe.steps,
                taste_profile="balanced",
            )
            ui.print_bottom_panel(
                f"{_('score', lang)}: {evaluation['score']}\n"
                f"{_('taste', lang)}: {evaluation['taste']}\n"
                f"{_('completion', lang)}: {evaluation['completion']}\n"
                f"{_('feedback', lang)}: {evaluation['feedback']}"
            )

        elif choice == "8":
            lang_choice = input(_("choose_lang", lang)).strip().lower()
            if lang_choice in TEXT:
                lang = lang_choice
                ui.lang = lang
                ui.print_bottom_panel(f"{_('current_lang', lang)}: {lang}")
            else:
                ui.print_bottom_panel(_("invalid", lang))

        elif choice == "9":
            print(_("thanks", lang))
            break

        else:
            ui.print_bottom_panel(_("invalid", lang))

        input("\n계속하려면 Enter를 누르세요...")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Cooking Simulator")
    parser.add_argument("--demo", action="store_true", help="자동 데모 실행")
    parser.add_argument("--cli", action="store_true", help="기존 콘솔 모드 실행")
    parser.add_argument("--lang", choices=["ko", "en", "ja", "zh"], default="ko", help="시스템 언어")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="Spoonacular API 키 (기본값: SPOONACULAR_API_KEY 환경 변수)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.demo:
        demo_run(args.lang, args.api_key)
        return
    if args.cli:
        interactive_loop(args.lang, args.api_key)
        return

    app = CookingGameGUI(args.lang, args.api_key)
    app.mainloop()


if __name__ == "__main__":
    main()
