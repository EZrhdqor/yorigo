const state = {
  recipes: [],
  selectedRecipe: null,
  inventory: {},
  language: ["ko", "en", "ja", "zh"].includes(localStorage.getItem("cooking-language"))
    ? localStorage.getItem("cooking-language")
    : "ko",
  cooking: false,
  completedSteps: [],
  addedIngredients: new Set(),
  cutIngredients: new Set(),
  heat: 2,
  remaining: 180,
  timerId: null,
  sceneItems: [],
  dragItem: null,
  dragOffset: { x: 0, y: 0 },
  languageRequest: 0,
  ready: false,
};

const $ = (selector) => document.querySelector(selector);
const canvas = $("#kitchen-canvas");
const context = canvas.getContext("2d");
const sourceText = new WeakMap();
const sourceAttributes = new WeakMap();
const translationCache = new Map();
const sceneSize = { width: 900, height: 420 };
let translationScheduled = false;
const canvasCopy = [
  "재료 준비대",
  "조리 냄비",
  "재료를 냄비로 끌어 넣으세요",
  "요리를 시작하면 재료를 담을 수 있어요",
  "레시피를 선택하면 조리 도구가 준비됩니다",
];

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `요청에 실패했습니다 (${response.status}).`);
  return data;
}

function setStatus(message) {
  $("#status").textContent = message;
  scheduleTranslation();
}

function scheduleTranslation() {
  if (!state.ready || state.language === "ko" || translationScheduled) return;
  translationScheduled = true;
  queueMicrotask(() => {
    translationScheduled = false;
    translatePage();
  });
}

function saveInventory() {
  localStorage.setItem("cooking-inventory", JSON.stringify(state.inventory));
  renderFridge();
}

function safeStoredInventory(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const entries = Object.entries(value);
  if (entries.some(([name, count]) => !name.trim() || name.length > 80 || !Number.isInteger(count) || count < 1 || count > 9999)) return null;
  return Object.fromEntries(entries);
}

function formatIngredients(ingredients) {
  if (!ingredients || !ingredients.length) return "재료 정보가 없습니다.";
  return ingredients.slice(0, 4).join(" · ") + (ingredients.length > 4 ? " · …" : "");
}

function renderRecipes() {
  const list = $("#recipe-list");
  list.replaceChildren();
  $("#recipe-count").textContent = String(state.recipes.length);
  if (!state.recipes.length) {
    const empty = document.createElement("p");
    empty.className = "empty-note";
    empty.textContent = "조건에 맞는 레시피가 없습니다. 다른 검색어를 입력해 보세요.";
    list.append(empty);
    scheduleTranslation();
    return;
  }
  for (const recipe of state.recipes) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `recipe-item${state.selectedRecipe?.name === recipe.name ? " selected" : ""}`;
    button.setAttribute("aria-pressed", String(state.selectedRecipe?.name === recipe.name));
    const title = document.createElement("strong");
    title.textContent = recipe.name;
    const details = document.createElement("span");
    details.textContent = `${recipe.cuisine || "기타"} · ${formatIngredients(recipe.ingredients)}`;
    button.append(title, details);
    button.addEventListener("click", () => selectRecipe(recipe));
    list.append(button);
  }
  scheduleTranslation();
}

function renderGuide() {
  const guide = $("#recipe-guide");
  guide.replaceChildren();
  if (!state.selectedRecipe) {
    const empty = document.createElement("p");
    empty.className = "empty-note";
    empty.textContent = "레시피를 선택하면 재료와 조리 순서를 알려드려요.";
    guide.append(empty);
    scheduleTranslation();
    return;
  }

  const recipe = state.selectedRecipe;
  const title = document.createElement("h3");
  title.textContent = recipe.name;
  const description = document.createElement("p");
  description.textContent = recipe.description || `${recipe.cuisine || "다양한"} 요리 레시피입니다.`;
  const ingredientTitle = document.createElement("p");
  ingredientTitle.textContent = "필요한 재료";
  const chips = document.createElement("div");
  chips.className = "ingredient-chips";
  for (const ingredient of recipe.ingredients || []) {
    const chip = document.createElement("span");
    chip.className = "ingredient-chip";
    chip.textContent = ingredient;
    chips.append(chip);
  }
  const stepsTitle = document.createElement("p");
  stepsTitle.textContent = "조리 순서";
  const steps = document.createElement("ol");
  for (const step of recipe.steps || []) {
    const item = document.createElement("li");
    item.textContent = step;
    steps.append(item);
  }
  guide.append(title, description, ingredientTitle, chips, stepsTitle, steps);
  scheduleTranslation();
}

function renderFridge() {
  const list = $("#fridge-list");
  list.replaceChildren();
  const entries = Object.entries(state.inventory).sort(([a], [b]) => a.localeCompare(b, "ko"));
  $("#ingredient-count").textContent = `${entries.length}종`;
  if (!entries.length) {
    const empty = document.createElement("li");
    empty.className = "fridge-empty";
    empty.textContent = "냉장고가 비어 있어요.";
    list.append(empty);
    scheduleTranslation();
    return;
  }
  for (const [name, quantity] of entries) {
    const item = document.createElement("li");
    item.className = "fridge-item";
    const label = document.createElement("span");
    label.textContent = `${name} · ${quantity}개`;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.setAttribute("aria-label", `${name} 하나 꺼내기`);
    remove.textContent = "−";
    remove.addEventListener("click", () => removeIngredient(name));
    item.append(label, remove);
    list.append(item);
  }
  scheduleTranslation();
}

function selectRecipe(recipe) {
  clearInterval(state.timerId);
  state.timerId = null;
  state.selectedRecipe = recipe;
  state.cooking = false;
  state.completedSteps = [];
  state.addedIngredients = new Set();
  state.cutIngredients = new Set();
  state.remaining = 180;
  resetScene();
  $("#start-button").disabled = false;
  $("#next-button").disabled = true;
  $("#evaluate-button").disabled = true;
  $("#cook-state").textContent = "레시피 준비 완료";
  $("#evaluation").hidden = true;
  $("#timer").textContent = "03:00";
  updateStepCount();
  renderRecipes();
  renderGuide();
  setStatus(`'${recipe.name}'을(를) 선택했습니다. 조리 시작을 눌러 보세요.`);
  drawScene();
}

function resetScene() {
  state.sceneItems = [];
  state.dragItem = null;
  if (!state.selectedRecipe) {
    drawScene();
    return;
  }
  (state.selectedRecipe.ingredients || []).slice(0, 8).forEach((name, index) => {
    state.sceneItems.push({
      id: `${index}`,
      ingredientIndex: index,
      name,
      x: 42 + (index % 2) * 157,
      y: 112 + Math.floor(index / 2) * 49,
      width: 137,
      height: 34,
      kind: "ingredient",
    });
  });
  state.sceneItems.push({ id: "knife", kind: "knife", x: 422, y: 286, width: 24, height: 76 });
  drawScene();
}

function updateStepCount() {
  const total = state.selectedRecipe?.steps?.length || 0;
  $("#step-count").textContent = `${state.completedSteps.length} / ${total}`;
}

function drawScene() {
  const { width: w, height: h } = sceneSize;
  context.clearRect(0, 0, w, h);
  context.fillStyle = "#eee4d2";
  context.fillRect(0, 0, w, h);
  context.fillStyle = "#e5d6be";
  roundRect(context, 22, 24, 397, 370, 18);
  context.fill();
  context.strokeStyle = "#d1b995";
  context.lineWidth = 2;
  context.stroke();
  context.fillStyle = "#7b6144";
  context.font = "600 15px 'Gowun Dodum', sans-serif";
  context.fillText(canvasText("재료 준비대"), 43, 62);

  context.fillStyle = "#c8b08d";
  roundRect(context, 482, 127, 336, 230, 40);
  context.fill();
  context.fillStyle = "#4e5053";
  context.beginPath();
  context.ellipse(655, 233, 147, 104, 0, 0, Math.PI * 2);
  context.fill();
  context.fillStyle = state.heat === 1 ? "#c4d2d0" : state.heat === 3 ? "#ebae86" : "#cfcbb6";
  context.beginPath();
  context.ellipse(655, 225, 125, 83, 0, 0, Math.PI * 2);
  context.fill();
  context.strokeStyle = "#e0e0d9";
  context.lineWidth = 5;
  context.stroke();
  context.fillStyle = "#4a4942";
  context.font = "600 14px 'Gowun Dodum', sans-serif";
  context.textAlign = "center";
  context.fillText(canvasText("조리 냄비"), 655, 354);
  context.font = "12px 'Gowun Dodum', sans-serif";
  const potIngredients = [...state.addedIngredients];
  if (potIngredients.length) {
    potIngredients.slice(-5).forEach((name, index) => context.fillText(name, 655, 203 + index * 19));
  } else {
    context.fillText(canvasText(state.cooking ? "재료를 냄비로 끌어 넣으세요" : "요리를 시작하면 재료를 담을 수 있어요"), 655, 230);
  }
  context.textAlign = "start";

  if (!state.selectedRecipe) {
    context.fillStyle = "#8c8069";
    context.font = "14px 'Gowun Dodum', sans-serif";
    context.textAlign = "center";
    context.fillText(canvasText("레시피를 선택하면 조리 도구가 준비됩니다"), 450, 390);
    context.textAlign = "start";
  } else {
    for (const item of state.sceneItems) drawItem(item);
  }
}

function roundRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  ctx.roundRect(x, y, width, height, radius);
}

function drawItem(item) {
  if (item.kind === "knife") {
    context.save();
    context.translate(item.x, item.y);
    context.fillStyle = "#a3acb2";
    context.beginPath();
    context.moveTo(12, 0);
    context.lineTo(24, 42);
    context.lineTo(16, 50);
    context.lineTo(8, 50);
    context.closePath();
    context.fill();
    context.fillStyle = "#74523b";
    roundRect(context, 5, 43, 14, 33, 5);
    context.fill();
    context.restore();
    return;
  }

  context.fillStyle = item.kind === "piece" ? "#f2c682" : "#f7dcae";
  roundRect(context, item.x, item.y, item.width, item.height, item.height / 2);
  context.fill();
  context.strokeStyle = "#94633a";
  context.lineWidth = 2;
  context.stroke();
  context.fillStyle = "#604629";
  context.font = "600 11px 'Gowun Dodum', sans-serif";
  context.textAlign = "center";
  const ingredientName = canvasText(item.name);
  context.fillText(item.kind === "piece" ? `${ingredientName} ½` : ingredientName, item.x + item.width / 2, item.y + item.height / 2 + 4, item.width - 8);
  context.textAlign = "start";
}

function canvasText(text) {
  if (state.language === "ko") return text;
  return translationCache.get(`${state.language}\u0000${text}`) || text;
}

function canvasPoint(event) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (event.clientX - rect.left) * (sceneSize.width / rect.width),
    y: (event.clientY - rect.top) * (sceneSize.height / rect.height),
  };
}

function hitItem(point) {
  return [...state.sceneItems].reverse().find((item) =>
    point.x >= item.x && point.x <= item.x + item.width &&
    point.y >= item.y && point.y <= item.y + item.height
  );
}

function pointerDown(event) {
  if (!state.cooking) return;
  const point = canvasPoint(event);
  const item = hitItem(point);
  if (!item) return;
  state.dragItem = item;
  state.dragOffset = { x: point.x - item.x, y: point.y - item.y };
  canvas.classList.add("dragging");
  canvas.setPointerCapture(event.pointerId);
}

function pointerMove(event) {
  if (!state.dragItem) return;
  const point = canvasPoint(event);
  const item = state.dragItem;
  item.x = Math.max(0, Math.min(sceneSize.width - item.width, point.x - state.dragOffset.x));
  item.y = Math.max(0, Math.min(sceneSize.height - item.height, point.y - state.dragOffset.y));
  if (item.kind === "knife") cutIngredientAt(item);
  drawScene();
}

function cutIngredientAt(knife) {
  const target = state.sceneItems.find((item) =>
    item.kind === "ingredient" && !state.cutIngredients.has(item.ingredientIndex) &&
    overlaps(knife, item)
  );
  if (!target) return;
  state.cutIngredients.add(target.ingredientIndex);
  state.sceneItems = state.sceneItems.filter((item) => item !== target);
  const pieceWidth = (target.width - 5) / 2;
  state.sceneItems.push(
    { ...target, id: `${target.id}-left`, kind: "piece", width: pieceWidth },
    { ...target, id: `${target.id}-right`, kind: "piece", x: target.x + pieceWidth + 5, width: pieceWidth },
  );
  setStatus(`${target.name}을(를) 반으로 잘랐습니다.`);
}

function overlaps(a, b) {
  return a.x < b.x + b.width && a.x + a.width > b.x &&
    a.y < b.y + b.height && a.y + a.height > b.y;
}

function pointerUp() {
  const item = state.dragItem;
  if (!item) return;
  if (item.kind !== "knife" && overlaps(item, { x: 530, y: 160, width: 250, height: 130 })) {
    const ingredient = item.name;
    if (!state.addedIngredients.has(ingredient)) {
      state.addedIngredients.add(ingredient);
      state.sceneItems = state.sceneItems.filter((candidate) => candidate.ingredientIndex !== item.ingredientIndex);
      setStatus(`${ingredient}을(를) 냄비에 넣었습니다.`);
    }
  }
  state.dragItem = null;
  canvas.classList.remove("dragging");
  drawScene();
}

async function searchRecipes(query = "") {
  $("#search-button").disabled = true;
  try {
    const data = await api(`/api/recipes?q=${encodeURIComponent(query)}`);
    state.recipes = data.recipes;
    state.selectedRecipe = null;
    state.cooking = false;
    clearInterval(state.timerId);
    state.timerId = null;
    renderRecipes();
    renderGuide();
    resetScene();
    $("#start-button").disabled = true;
    $("#next-button").disabled = true;
    $("#evaluate-button").disabled = true;
    $("#recipe-source").textContent = data.api_available ? "Spoonacular 레시피" : "기본 레시피";
    setStatus(data.recipes.length ? `${data.recipes.length}개의 레시피를 찾았습니다.` : "검색 결과가 없습니다.");
  } catch (error) {
    setStatus(error.message);
  } finally {
    $("#search-button").disabled = false;
  }
}

async function recommendRecipes() {
  $("#recommend-button").disabled = true;
  try {
    const data = await api("/api/recommend", {
      method: "POST",
      body: JSON.stringify({ inventory: state.inventory }),
    });
    state.recipes = data.recipes;
    state.selectedRecipe = null;
    state.cooking = false;
    clearInterval(state.timerId);
    state.timerId = null;
    renderRecipes();
    renderGuide();
    resetScene();
    $("#start-button").disabled = true;
    $("#next-button").disabled = true;
    $("#evaluate-button").disabled = true;
    $("#recipe-source").textContent = data.mode === "popular" ? "인기 레시피 추천" : "보유 재료로 만들 수 있는 요리";
    setStatus(data.mode === "popular" ? "만들 수 있는 요리가 없어 인기 레시피를 추천했어요." : `냉장고 재료로 ${data.recipes.length}개 요리를 추천했어요.`);
  } catch (error) {
    setStatus(error.message);
  } finally {
    $("#recommend-button").disabled = false;
  }
}

async function addIngredient(event) {
  event.preventDefault();
  const nameInput = $("#ingredient-name");
  const quantityInput = $("#ingredient-quantity");
  const name = nameInput.value.trim();
  const quantity = Number(quantityInput.value);
  try {
    const data = await api("/api/fridge/add", {
      method: "POST",
      body: JSON.stringify({ inventory: state.inventory, name, quantity }),
    });
    if (!data.inventory || typeof data.inventory !== "object" || Array.isArray(data.inventory)) {
      throw new Error("서버에서 냉장고 목록을 받지 못했습니다. 웹 서버를 다시 시작해 주세요.");
    }
    state.inventory = data.inventory;
    saveInventory();
    nameInput.value = "";
    quantityInput.value = "1";
    setStatus(data.message);
    nameInput.focus();
  } catch (error) {
    setStatus(error.message);
  }
}

async function removeIngredient(name) {
  try {
    const data = await api("/api/fridge/remove", {
      method: "POST",
      body: JSON.stringify({ inventory: state.inventory, name, quantity: 1 }),
    });
    if (!data.inventory || typeof data.inventory !== "object" || Array.isArray(data.inventory)) {
      throw new Error("서버에서 냉장고 목록을 받지 못했습니다. 웹 서버를 다시 시작해 주세요.");
    }
    state.inventory = data.inventory;
    saveInventory();
    setStatus(data.message);
  } catch (error) {
    setStatus(error.message);
  }
}

function startCooking() {
  if (!state.selectedRecipe) return;
  state.cooking = true;
  state.completedSteps = [];
  state.addedIngredients.clear();
  state.cutIngredients.clear();
  state.remaining = 180;
  resetScene();
  updateTimer();
  updateStepCount();
  $("#cook-state").textContent = "조리 중";
  $("#start-button").disabled = true;
  $("#next-button").disabled = false;
  $("#evaluate-button").disabled = false;
  $("#evaluation").hidden = true;
  setStatus("재료를 냄비에 넣고 칼로 손질해 보세요. 조리 단계를 진행할 수 있어요.");
  state.timerId = setInterval(() => {
    state.remaining = Math.max(0, state.remaining - 1);
    updateTimer();
    if (state.remaining === 0) {
      clearInterval(state.timerId);
      state.timerId = null;
      state.cooking = false;
      $("#cook-state").textContent = "시간 종료";
      setStatus("조리 시간이 끝났어요. 요리 평가를 확인해 보세요.");
    }
  }, 1000);
}

function updateTimer() {
  const minutes = Math.floor(state.remaining / 60);
  const seconds = state.remaining % 60;
  $("#timer").textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function nextStep() {
  if (!state.cooking || !state.selectedRecipe) return;
  const steps = state.selectedRecipe.steps || [];
  if (state.completedSteps.length >= steps.length) {
    setStatus("모든 조리 단계를 완료했어요.");
    return;
  }
  state.completedSteps.push(steps[state.completedSteps.length]);
  updateStepCount();
  const current = state.completedSteps.length;
  if (current >= steps.length) {
    clearInterval(state.timerId);
    state.timerId = null;
    state.cooking = false;
    $("#cook-state").textContent = "조리 완료";
    setStatus("모든 조리 단계를 완료했어요. 요리를 평가해 보세요.");
  } else {
    setStatus(`다음 단계: ${steps[current]}`);
  }
}

async function evaluateCooking() {
  if (!state.selectedRecipe) return;
  $("#evaluate-button").disabled = true;
  try {
    const data = await api("/api/evaluate", {
      method: "POST",
      body: JSON.stringify({
        recipe: state.selectedRecipe,
        selected_ingredients: [...state.addedIngredients],
        completed_steps: state.completedSteps,
      }),
    });
    const panel = $("#evaluation");
    panel.replaceChildren();
    const score = document.createElement("div");
    score.className = "evaluation-score";
    score.textContent = `${data.score}점`;
    const feedback = document.createElement("p");
    feedback.textContent = `${data.taste} · ${data.completion}\n${data.feedback}`;
    panel.append(score, feedback);
    panel.hidden = false;
    setStatus("요리 평가를 완료했어요.");
    scheduleTranslation();
  } catch (error) {
    setStatus(error.message);
  } finally {
    $("#evaluate-button").disabled = false;
  }
}

async function translatePage() {
  const target = state.language;
  const version = ++state.languageRequest;
  const root = document.querySelector(".page-shell");
  const nodes = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (!node.nodeValue.trim() || node.parentElement?.closest("#language-select")) continue;
    if (!sourceText.has(node)) sourceText.set(node, node.nodeValue);
    nodes.push(node);
  }
  const attributes = [];
  for (const element of root.querySelectorAll("[placeholder], [title]")) {
    if (element.id === "language-select") continue;
    for (const attribute of ["placeholder", "title"]) {
      if (!element.hasAttribute(attribute)) continue;
      let originals = sourceAttributes.get(element);
      if (!originals) {
        originals = {};
        sourceAttributes.set(element, originals);
      }
      if (!(attribute in originals)) originals[attribute] = element.getAttribute(attribute);
      attributes.push({ element, attribute, text: originals[attribute] });
    }
  }
  const entries = [
    ...nodes.map((node) => ({ node, text: sourceText.get(node) })),
    ...attributes.map((entry) => ({ ...entry })),
  ];
  const visibleCanvasText = [
    ...canvasCopy,
    ...(state.selectedRecipe?.ingredients || []).slice(0, 8),
  ];
  const translatedCanvasText = [...new Set(visibleCanvasText)].map((text) => ({ text, canvas: true }));
  entries.push(...translatedCanvasText);
  if (target === "ko") {
    for (const entry of entries) {
      if (entry.node) entry.node.nodeValue = entry.text;
      else if (entry.element) entry.element.setAttribute(entry.attribute, entry.text);
    }
    drawScene();
    return;
  }
  try {
    const translated = [];
    const uncached = [];
    for (const entry of entries) {
      const key = `${target}\u0000${entry.text}`;
      if (translationCache.has(key)) translated.push(translationCache.get(key));
      else {
        translated.push(null);
        uncached.push({ index: translated.length - 1, text: entry.text });
      }
    }
    for (let offset = 0; offset < uncached.length; offset += 100) {
      const batch = uncached.slice(offset, offset + 100);
      const data = await api("/api/translate", {
        method: "POST",
        body: JSON.stringify({ target, texts: batch.map((item) => item.text) }),
      });
      batch.forEach((item, index) => {
        translated[item.index] = data.translations[index];
        translationCache.set(`${target}\u0000${item.text}`, data.translations[index]);
      });
    }
    if (version !== state.languageRequest || target !== state.language) return;
    entries.forEach((entry, index) => {
      if (entry.node) entry.node.nodeValue = translated[index];
      else if (entry.element) entry.element.setAttribute(entry.attribute, translated[index]);
    });
    drawScene();
  } catch (error) {
    if (version !== state.languageRequest) return;
    state.language = "ko";
    localStorage.setItem("cooking-language", "ko");
    $("#language-select").value = "ko";
    await translatePage();
    $("#status").textContent = `번역 실패: ${error.message}`;
  }
}

function bindEvents() {
  $("#search-button").addEventListener("click", () => searchRecipes($("#recipe-search").value.trim()));
  $("#recipe-search").addEventListener("keydown", (event) => {
    if (event.key === "Enter") searchRecipes(event.currentTarget.value.trim());
  });
  $("#recommend-button").addEventListener("click", recommendRecipes);
  $("#ingredient-form").addEventListener("submit", addIngredient);
  $("#clear-fridge").addEventListener("click", () => {
    state.inventory = {};
    saveInventory();
    setStatus("냉장고를 비웠어요.");
  });
  $("#start-button").addEventListener("click", startCooking);
  $("#next-button").addEventListener("click", nextStep);
  $("#evaluate-button").addEventListener("click", evaluateCooking);
  $("#language-select").value = state.language;
  $("#language-select").addEventListener("change", (event) => {
    state.language = event.target.value;
    localStorage.setItem("cooking-language", state.language);
    if (state.language === "ko") translatePage();
    else scheduleTranslation();
  });
  document.querySelectorAll("[data-heat]").forEach((button) => {
    button.addEventListener("click", () => {
      state.heat = Number(button.dataset.heat);
      document.querySelectorAll("[data-heat]").forEach((item) => item.classList.toggle("active", item === button));
      drawScene();
    });
  });
  canvas.addEventListener("pointerdown", pointerDown);
  canvas.addEventListener("pointermove", pointerMove);
  canvas.addEventListener("pointerup", pointerUp);
  canvas.addEventListener("pointercancel", pointerUp);
}

async function initialize() {
  bindEvents();
  try {
    const data = await api("/api/bootstrap");
    state.recipes = data.recipes;
    let storedInventory = null;
    try {
      storedInventory = JSON.parse(localStorage.getItem("cooking-inventory") || "null");
    } catch {
      localStorage.removeItem("cooking-inventory");
    }
    const saved = safeStoredInventory(storedInventory);
    state.inventory = saved || data.inventory;
    if (!saved) localStorage.setItem("cooking-inventory", JSON.stringify(state.inventory));
    renderRecipes();
    renderFridge();
    renderGuide();
    $("#recipe-source").textContent = data.api_available ? "Spoonacular 레시피" : "기본 레시피";
    drawScene();
    state.ready = true;
    setStatus(data.api_available ? "Spoonacular 레시피를 불러왔어요." : "기본 레시피를 불러왔어요. API 키와 네트워크를 확인할 수 있습니다.");
  } catch (error) {
    setStatus(`웹 앱을 준비하지 못했습니다: ${error.message}`);
  }
}

initialize();
