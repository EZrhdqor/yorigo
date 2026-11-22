const RECIPE_URL = "https://api.spoonacular.com/recipes/complexSearch";
const TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2";
const RECOMMENDATION_LIMIT = 5;

const DEFAULT_RECIPES = [
  {
    name: "김치볶음밥",
    cuisine: "한식",
    ingredients: ["김치", "밥", "계란", "양파", "파"],
    tools: ["팬", "뒤집개"],
    steps: [
      "팬을 예열하고 양파를 넣어 약불에서 향을 냅니다.",
      "김치를 넣고 볶아 숨을 죽입니다.",
      "밥을 넣고 고루 섞습니다.",
      "계란을 풀어 넣고 휘저어 익힙니다.",
      "파를 올려 완성합니다.",
    ],
    taste_profile: "매콤",
    difficulty: 2,
    description: "매콤한 김치와 고소한 계란이 어우러진 든든한 한 끼",
    source: "local",
  },
  {
    name: "토마토파스타",
    cuisine: "이탈리아",
    ingredients: ["토마토", "양파", "마늘", "스파게티", "올리브오일"],
    tools: ["냄비", "팬"],
    steps: [
      "팬에 올리브오일을 두르고 마늘과 양파를 볶습니다.",
      "토마토를 넣고 약한 불로 끓입니다.",
      "삶은 스파게티를 넣고 소스를 섞습니다.",
      "마지막에 간을 맞춰 완성합니다.",
    ],
    taste_profile: "상큼",
    difficulty: 3,
    description: "상큼하고 담백한 토마토 소스 파스타",
    source: "local",
  },
  {
    name: "계란볶음밥",
    cuisine: "한식",
    ingredients: ["밥", "계란", "양파", "당근", "파"],
    tools: ["팬", "뒤집개"],
    steps: [
      "팬에 양파와 당근을 살짝 볶습니다.",
      "밥을 넣고 고루 섞습니다.",
      "계란을 넣고 저어가며 익힙니다.",
      "파를 추가해 마무리합니다.",
    ],
    taste_profile: "고소",
    difficulty: 1,
    description: "간단하고 든든한 계란볶음밥",
    source: "local",
  },
  {
    name: "김치찌개",
    cuisine: "한식",
    ingredients: ["김치", "두부", "양파", "파"],
    tools: ["냄비"],
    steps: [
      "냄비에 김치와 양파를 넣고 볶습니다.",
      "물을 붓고 끓인 뒤 두부를 넣습니다.",
      "파를 넣고 한소끔 더 끓여 완성합니다.",
    ],
    taste_profile: "매콤",
    difficulty: 2,
    description: "김치와 두부를 넣어 끓인 얼큰한 찌개",
    source: "local",
  },
  {
    name: "토마토 달걀볶음",
    cuisine: "중식",
    ingredients: ["토마토", "계란", "양파", "파"],
    tools: ["팬"],
    steps: [
      "토마토와 양파를 먹기 좋게 썹니다.",
      "팬에 양파와 토마토를 넣고 볶습니다.",
      "계란을 넣어 부드럽게 익힌 뒤 파를 올립니다.",
    ],
    taste_profile: "고소",
    difficulty: 1,
    description: "토마토와 달걀을 부드럽게 볶은 간단한 요리",
    source: "local",
  },
];

const INITIAL_INVENTORY = {
  토마토: 2,
  양파: 2,
  계란: 4,
  김치: 1,
  밥: 2,
  파: 2,
  마늘: 1,
  올리브오일: 1,
  두부: 1,
  치즈: 1,
  스파게티: 1,
  당근: 1,
  버섯: 1,
  우유: 1,
};

const INGREDIENT_ALIASES = {
  토마토: ["tomato", "tomatoes"],
  양파: ["onion", "onions"],
  감자: ["potato", "potatoes"],
  버섯: ["mushroom", "mushrooms"],
  파: ["green onion", "spring onion", "scallion", "leek"],
  계란: ["egg", "eggs"],
  김치: ["kimchi"],
  밥: ["rice"],
  치즈: ["cheese"],
  스파게티: ["spaghetti", "pasta"],
  마늘: ["garlic"],
  두부: ["tofu"],
  참치: ["tuna"],
  오징어: ["squid"],
  고추장: ["gochujang"],
  간장: ["soy sauce"],
  올리브오일: ["olive oil"],
  당근: ["carrot", "carrots"],
  브로콜리: ["broccoli"],
  베이컨: ["bacon"],
  우유: ["milk"],
  딸기: ["strawberry", "strawberries"],
  바나나: ["banana", "bananas"],
};

const TASTE_ALIASES = {
  balanced: ["고소", "상큼", "매콤", "balanced"],
};

const translationCache = new Map();
let recipeCatalogCache = null;
let recipeCatalogCacheExpires = 0;

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

function error(message, status = 400) {
  return json({ error: message }, status);
}

async function readJson(request) {
  try {
    const text = await request.text();
    if (text.length > 64 * 1024) return { error: "요청 내용이 너무 큽니다." };
    return { data: text ? JSON.parse(text) : {} };
  } catch {
    return { error: "JSON 요청 형식이 올바르지 않습니다." };
  }
}

function validateInventory(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const inventory = Object.create(null);
  for (const [rawName, quantity] of Object.entries(value)) {
    const name = rawName.trim();
    if (!name || name.length > 80 || !Number.isInteger(quantity) || quantity < 1 || quantity > 9999) {
      return null;
    }
    inventory[name] = quantity;
  }
  return inventory;
}

function cleanHtml(value) {
  return String(value || "")
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .trim();
}

function mapRecipe(row) {
  if (!row || typeof row !== "object" || typeof row.title !== "string" || !row.title.trim()) return null;
  const ingredients = Array.isArray(row.extendedIngredients)
    ? row.extendedIngredients
      .map((item) => item?.original || item?.name)
      .filter((name) => typeof name === "string" && name.trim())
      .map((name) => name.trim())
    : [];
  const steps = [];
  if (Array.isArray(row.analyzedInstructions)) {
    for (const group of row.analyzedInstructions) {
      if (!Array.isArray(group?.steps)) continue;
      for (const step of group.steps) {
        if (typeof step?.step === "string" && step.step.trim()) steps.push(step.step.trim());
      }
    }
  }
  if (!steps.length) {
    const instructions = cleanHtml(row.instructions);
    if (instructions) steps.push(...instructions.split(/[\r\n]+|(?<=[.!?])\s+/).filter(Boolean));
  }
  const description = cleanHtml(row.summary)
    || (row.readyInMinutes ? `조리 시간 약 ${row.readyInMinutes}분` : "Spoonacular에서 제공된 레시피입니다.");
  const searchableText = `${description} ${ingredients.join(" ")}`.toLowerCase();
  const taste = /매콤|고추|김치|불맛|떡볶이/.test(searchableText)
    ? "매콤"
    : /새콤|상큼|토마토|레몬|산미/.test(searchableText)
      ? "상큼"
      : /고소|버터|치즈|달걀|크림/.test(searchableText)
        ? "고소"
        : "balanced";
  return {
    name: row.title.trim(),
    cuisine: Array.isArray(row.cuisines) && row.cuisines.length ? row.cuisines.join(", ") : "기타",
    ingredients: ingredients.length ? ingredients : ["재료를 확인하세요"],
    tools: ["팬"],
    steps: steps.length ? steps : ["레시피 상세를 확인해 주세요."],
    taste_profile: taste,
    difficulty: 2,
    description,
    source: "spoonacular",
  };
}

async function fetchRecipes({ query = "", sort = "", limit = 30 } = {}) {
  const key = process.env.SPOONACULAR_API_KEY;
  if (key) {
    const url = new URL(RECIPE_URL);
    url.searchParams.set("apiKey", key);
    url.searchParams.set("number", String(Math.max(1, Math.min(limit, 100))));
    url.searchParams.set("addRecipeInformation", "true");
    url.searchParams.set("fillIngredients", "true");
    url.searchParams.set("instructionsRequired", "true");
    if (query) url.searchParams.set("query", query);
    if (sort) url.searchParams.set("sort", sort);
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(12000) });
      if (!response.ok) {
        console.warn(`Spoonacular request failed: HTTP ${response.status}`);
      } else {
        const payload = await response.json();
        const recipes = Array.isArray(payload?.results) ? payload.results.map(mapRecipe).filter(Boolean) : [];
        if (recipes.length) return recipes;
      }
    } catch (requestError) {
      console.warn("Spoonacular request failed:", requestError?.name || "network error");
    }
  }

  if (sort === "popularity") return DEFAULT_RECIPES.slice(0, limit);
  if (query) {
    const term = query.toLocaleLowerCase();
    return DEFAULT_RECIPES.filter((recipe) =>
      recipe.name.toLocaleLowerCase().includes(term)
      || recipe.description.toLocaleLowerCase().includes(term)
      || recipe.ingredients.some((ingredient) => ingredient.toLocaleLowerCase().includes(term))
    ).slice(0, limit);
  }
  return DEFAULT_RECIPES.slice(0, limit);
}

async function getRecipeCatalog() {
  if (recipeCatalogCache && Date.now() < recipeCatalogCacheExpires) return recipeCatalogCache;
  recipeCatalogCache = await fetchRecipes({ limit: 30 });
  recipeCatalogCacheExpires = Date.now() + 10 * 60 * 1000;
  return recipeCatalogCache;
}

function ingredientAvailable(recipeIngredient, inventory) {
  const normalized = recipeIngredient.toLocaleLowerCase();
  return Object.entries(inventory).some(([available, quantity]) => {
    if (quantity <= 0) return false;
    if (normalized.includes(available.toLocaleLowerCase())) return true;
    return (INGREDIENT_ALIASES[available] || []).some((alias) =>
      new RegExp(`(^|[^\\w])${alias.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}([^\\w]|$)`, "i").test(normalized)
    );
  });
}

function findCookable(recipes, inventory, limit) {
  const seen = new Set();
  return recipes.filter((recipe) => {
    if (!recipe.ingredients?.length || !recipe.ingredients.every((name) => ingredientAvailable(name, inventory))) return false;
    const key = recipe.name.toLocaleLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  }).sort((a, b) => {
    const tasteA = (TASTE_ALIASES.balanced || ["balanced"]).includes(a.taste_profile);
    const tasteB = (TASTE_ALIASES.balanced || ["balanced"]).includes(b.taste_profile);
    return Number(tasteB) - Number(tasteA) || a.difficulty - b.difficulty || a.name.localeCompare(b.name);
  }).slice(0, limit);
}

function detectLanguage(text) {
  if (/[\uac00-\ud7af]/u.test(text)) return "ko";
  if (/[\u3040-\u30ff]/u.test(text)) return "ja";
  if (/[\u4e00-\u9fff]/u.test(text)) return "zh";
  return null;
}

async function translateMany(texts, target) {
  if (target === "ko") return texts;
  const key = process.env.GOOGLE_TRANSLATE_API_KEY;
  if (!key) throw new Error("GOOGLE_TRANSLATE_API_KEY 환경 변수를 Netlify 사이트에 설정해 주세요.");
  const results = new Array(texts.length);
  const pending = new Map();
  texts.forEach((text, index) => {
    const cacheKey = `${target}\u0000${text}`;
    if (translationCache.has(cacheKey)) results[index] = translationCache.get(cacheKey);
    else {
      const indices = pending.get(text) || [];
      indices.push(index);
      pending.set(text, indices);
    }
  });

  const groups = new Map();
  for (const text of pending.keys()) {
    const source = detectLanguage(text);
    const group = groups.get(source) || [];
    group.push(text);
    groups.set(source, group);
  }

  for (const [source, uniqueTexts] of groups) {
    for (let offset = 0; offset < uniqueTexts.length; offset += 50) {
      const batch = uniqueTexts.slice(offset, offset + 50);
      const payload = { q: batch, target, format: "text" };
      if (source) payload.source = source;
      const response = await fetch(TRANSLATE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8", "X-Goog-Api-Key": key },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(12000),
      });
      if (!response.ok) throw new Error(`Google Cloud Translation 요청 실패 (HTTP ${response.status}).`);
      const data = await response.json();
      const translations = data?.data?.translations;
      if (!Array.isArray(translations) || translations.length !== batch.length) {
        throw new Error("Google Cloud Translation 응답 형식이 올바르지 않습니다.");
      }
      batch.forEach((text, index) => {
        const translated = translations[index]?.translatedText;
        if (typeof translated !== "string") throw new Error("번역 결과에 올바르지 않은 항목이 있습니다.");
        const decoded = cleanHtml(translated);
        translationCache.set(`${target}\u0000${text}`, decoded);
        for (const resultIndex of pending.get(text)) results[resultIndex] = decoded;
      });
    }
  }
  return results;
}

function calculateEvaluation(recipe, selected, completed) {
  const matched = recipe.ingredients.filter((ingredient) => selected.includes(ingredient)).length;
  const ingredientRatio = matched / Math.max(recipe.ingredients.length, 1);
  const processRatio = Math.min(completed.length / Math.max(recipe.steps.length, 1), 1);
  const total = Math.max(0, Math.min(Math.floor(ingredientRatio * 60 + processRatio * 25 + 10), 100));
  let taste;
  let completion;
  let feedback;
  if (total >= 85) {
    taste = "매우 맛있다";
    completion = "완성도 높음";
    feedback = "식감과 밸런스가 훌륭합니다. 다음에도 이 조합으로 만들면 좋습니다.";
  } else if (total >= 70) {
    taste = "좋은 편이다";
    completion = "대체로 완성됨";
    feedback = "재료의 조합은 좋지만, 간과 조리 시간을 조금 더 조정하면 더 맛있어집니다.";
  } else if (total >= 50) {
    taste = "보통이다";
    completion = "조금 더 보완 필요";
    feedback = "기본 맛은 괜찮지만, 재료를 더 신선하게 넣거나 조리 시간을 늘려보세요.";
  } else {
    taste = "아쉬운 편이다";
    completion = "재조정 필요";
    feedback = "레시피와 재료의 조합이 많이 어긋났습니다. 재료를 다시 확인해 보세요.";
  }
  return { score: total, taste, completion, feedback, matched_count: matched, required_count: recipe.ingredients.length };
}

async function handle(request) {
  const url = new URL(request.url);
  const pathname = url.pathname;
  const functionPrefix = "/.netlify/functions/api/";
  const route = pathname.startsWith(functionPrefix)
    ? pathname.slice(functionPrefix.length)
    : pathname.replace(/^\/api\/?/, "");

  if (request.method === "GET" && route === "bootstrap") {
    const recipes = await getRecipeCatalog();
    return json({
      recipes,
      inventory: INITIAL_INVENTORY,
      api_available: recipes.some((recipe) => recipe.source === "spoonacular"),
    });
  }

  if (request.method === "GET" && route === "recipes") {
    const query = (url.searchParams.get("q") || "").trim();
    if (query.length > 120) return error("검색어는 120자 이내로 입력해 주세요.");
    const recipes = await fetchRecipes({ query });
    return json({ recipes, api_available: recipes.some((recipe) => recipe.source === "spoonacular") });
  }

  if (request.method !== "POST") return error("요청을 처리할 수 없습니다.", 405);
  const parsed = await readJson(request);
  if (parsed.error) return error(parsed.error);
  const payload = parsed.data;
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return error("요청 형식이 올바르지 않습니다.");

  if (route === "recommend") {
    const inventory = validateInventory(payload.inventory);
    if (!inventory) return error("재료 목록 형식이 올바르지 않습니다.");
    const catalog = await getRecipeCatalog();
    const available = findCookable([...catalog, ...DEFAULT_RECIPES], inventory, RECOMMENDATION_LIMIT);
    if (available.length) return json({ recipes: available, mode: "ingredients" });
    const popular = await fetchRecipes({ sort: "popularity", limit: RECOMMENDATION_LIMIT });
    const unique = [...new Map([...popular, ...DEFAULT_RECIPES].map((recipe) => [recipe.name.toLocaleLowerCase(), recipe])).values()]
      .slice(0, RECOMMENDATION_LIMIT);
    return json({ recipes: unique, mode: "popular" });
  }

  if (route === "fridge/add") {
    const inventory = validateInventory(payload.inventory);
    const name = typeof payload.name === "string" ? payload.name.trim() : "";
    const quantity = payload.quantity;
    if (!inventory) return error("재료 목록 형식이 올바르지 않습니다.");
    if (!name || name.length > 80) return error("재료 이름을 1~80자로 입력해 주세요.");
    if (!Number.isInteger(quantity) || quantity < 1 || quantity > 9999) {
      return error("수량은 1~9999 사이의 정수로 입력해 주세요.");
    }
    if ((inventory[name] || 0) + quantity > 9999) return error("재료별 보관 수량은 9999개까지입니다.");
    inventory[name] = (inventory[name] || 0) + quantity;
    return json({ inventory, message: `${name} ${quantity}개를 냉장고에 저장했습니다.` });
  }

  if (route === "fridge/remove") {
    const inventory = validateInventory(payload.inventory);
    const name = typeof payload.name === "string" ? payload.name.trim() : "";
    const quantity = payload.quantity ?? 1;
    if (!inventory) return error("재료 목록 형식이 올바르지 않습니다.");
    if (!name) return error("꺼낼 재료를 선택해 주세요.");
    if (!Number.isInteger(quantity) || quantity < 1) return error("수량은 1 이상의 정수로 입력해 주세요.");
    if ((inventory[name] || 0) < quantity) return error("냉장고에 해당 수량의 재료가 없습니다.");
    inventory[name] -= quantity;
    if (inventory[name] === 0) delete inventory[name];
    return json({ inventory, message: `${name} ${quantity}개를 냉장고에서 꺼냈습니다.` });
  }

  if (route === "translate") {
    const { target, texts } = payload;
    if (!["ko", "en", "ja", "zh"].includes(target)) return error("지원하지 않는 언어입니다.");
    if (!Array.isArray(texts) || texts.length > 100 || texts.some((text) => typeof text !== "string" || text.length > 2000)) {
      return error("번역할 문장 목록이 올바르지 않습니다.");
    }
    try {
      return json({ translations: await translateMany(texts, target) });
    } catch (translationError) {
      console.warn("Translation request failed:", translationError?.name || "request error");
      return error(translationError.message || "번역 요청에 실패했습니다.", 503);
    }
  }

  if (route === "evaluate") {
    const recipe = payload.recipe;
    if (!recipe || typeof recipe !== "object" || Array.isArray(recipe)) return error("평가할 레시피가 없습니다.");
    if (!Array.isArray(recipe.ingredients) || !recipe.ingredients.length || recipe.ingredients.length > 100
      || recipe.ingredients.some((item) => typeof item !== "string")
      || !Array.isArray(recipe.steps) || !recipe.steps.length || recipe.steps.length > 100
      || recipe.steps.some((item) => typeof item !== "string")) {
      return error("레시피 정보가 올바르지 않습니다.");
    }
    const { selected_ingredients: selected, completed_steps: completed } = payload;
    if (!Array.isArray(selected) || selected.some((item) => !recipe.ingredients.includes(item))
      || !Array.isArray(completed) || completed.some((item) => !recipe.steps.includes(item))) {
      return error("평가 정보의 형식이 올바르지 않습니다.");
    }
    return json(calculateEvaluation(recipe, selected, completed));
  }

  return error("요청 경로를 찾을 수 없습니다.", 404);
}

export default async (request) => {
  try {
    return await handle(request);
  } catch (requestError) {
    console.error("Netlify API function failed:", requestError?.name || "request error");
    return error("서버에서 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.", 500);
  }
};
