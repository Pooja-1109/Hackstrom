const intervals = [1, 3, 7, 14, 30];

function getToday() {
  return new Date().toISOString().split("T")[0];
}

function addDays(date, days) {
  let result = new Date(date);
  result.setDate(result.getDate() + days);
  return result.toISOString().split("T")[0];
}

function getData() {
  return JSON.parse(localStorage.getItem("insights")) || [];
}

function saveData(data) {
  localStorage.setItem("insights", JSON.stringify(data));
}

// Add Insight
function addInsight() {
  let text = document.getElementById("insightText").value;
  let topic = document.getElementById("topic").value;

  if (!text) return alert("Enter insight!");

  let data = getData();

  data.push({
    id: Date.now(),
    text,
    topic,
    intervalIndex: 0,
    nextReviewDate: addDays(new Date(), 1),
    success: 0,
    fail: 0
  });

  saveData(data);
  alert("Saved!");
  location.reload();
}

// Load Reviews
function loadReview() {
  let data = getData();
  let today = getToday();

  let due = data.filter(item => item.nextReviewDate === today);

  document.getElementById("reminder").innerText =
    `⚠️ You have ${due.length} items to review today`;

  let box = document.getElementById("reviewBox");
  box.innerHTML = "";

  due.forEach(item => {
    let div = document.createElement("div");
    div.className = "card";

    div.innerHTML = `
      <p><b>Topic:</b> ${item.topic}</p>
      <p>${item.text}</p>
      <button onclick="markRemember(${item.id})">Remember</button>
      <button onclick="markForgot(${item.id})">Forgot</button>
    `;

    box.appendChild(div);
  });
}

// Remember
function markRemember(id) {
  let data = getData();

  data = data.map(item => {
    if (item.id === id) {
      item.intervalIndex = Math.min(item.intervalIndex + 1, intervals.length - 1);
      item.nextReviewDate = addDays(new Date(), intervals[item.intervalIndex]);
      item.success++;
    }
    return item;
  });

  saveData(data);
  location.reload();
}

// Forgot
function markForgot(id) {
  let data = getData();

  data = data.map(item => {
    if (item.id === id) {
      item.intervalIndex = 0;
      item.nextReviewDate = addDays(new Date(), 1);
      item.fail++;
    }
    return item;
  });

  saveData(data);
  location.reload();
}

// Dashboard
function loadStats() {
  let data = getData();

  let total = data.length;
  let success = data.reduce((sum, i) => sum + i.success, 0);
  let fail = data.reduce((sum, i) => sum + i.fail, 0);

  let attempts = success + fail;
  let retention = attempts ? ((success / attempts) * 100).toFixed(2) : 0;

  document.getElementById("stats").innerText =
    `Total Insights: ${total} | Retention: ${retention}%`;
}

// Init
loadReview();
loadStats();