/**
 * Digital Literacy Bridge - Frontend Application
 *
 * Vanilla JS SPA with accessibility-first patterns.
 * Uses hash-based routing: #home, #course/slug, #lesson/id
 */

class AccessibilityAnnouncer {
  constructor() {
    this.el = document.createElement("div");
    this.el.setAttribute("aria-live", "polite");
    this.el.setAttribute("aria-atomic", "true");
    this.el.className = "sr-only";
    document.body.appendChild(this.el);
  }
  announce(message) {
    this.el.textContent = message;
    setTimeout(() => { this.el.textContent = ""; }, 1000);
  }
}

class A11yAnnouncer {
  constructor() {
    this.container = document.createElement("div");
    this.container.setAttribute("aria-live", "polite");
    this.container.setAttribute("aria-atomic", "false");
    this.container.className = "sr-only";
    document.body.appendChild(this.container);
  }
  announce(message, priority = "polite") {
    this.container.setAttribute("aria-live", priority);
    this.container.textContent = message;
    setTimeout(() => {
      this.container.textContent = "";
      this.container.removeAttribute("aria-live");
    }, 3000);
  }
}

class App {
  constructor() {
    this.root = document.getElementById("app");
    this.announcer = new AccessibilityAnnouncer();
    this.user = null;
    this.courses = [];
    this.currentRoute = "";
    this.ttsEnabled = false;
    this.ttsVoice = null;
    this.synth = window.speechSynthesis;
  }

  async init() {
    await this.loadUserPreferences();
    await this.setupEventListeners();
    await this.fetchInitialData();
    await this.handleRoute(); // Will set currentRoute and render
  }

  async loadUserPreferences() {
    // Text size
    const savedSize = localStorage.getItem("dlb_font_size");
    if (savedSize) {
      document.documentElement.style.setProperty("--font-size-base", savedSize + "px");
    }
    // Language
    const savedLang = localStorage.getItem("dlb_language");
    if (savedLang) {
      window.api.setLanguage(savedLang);
      document.getElementById("lang-toggle").textContent = this.getLangDisplay(savedLang);
    }
    // TTS
    this.ttsEnabled = localStorage.getItem("dlb_tts") === "true";
    this.updateTTSButton();
    if (this.synth) {
      const voices = this.synth.getVoices();
      this.ttsVoice = voices.find(v => v.lang.startsWith(window.api.language)) || voices[0];
    }
  }

  getLangDisplay(code) {
    const names = { en: "English", es: "Español", fr: "Français", pt: "Português" };
    return names[code] || code.toUpperCase();
  }

  setupEventListeners() {
    // Language toggle
    document.getElementById("lang-toggle").addEventListener("click", () => this.cycleLanguage());
    // Text size toggle
    document.getElementById("text-size-toggle").addEventListener("click", () => this.cycleTextSize());
    // TTS toggle
    document.getElementById("tts-toggle").addEventListener("click", () => this.toggleTTS());
    // Hash change for routing
    window.addEventListener("hashchange", () => this.handleRoute());
    // Delegate clicks inside app
    this.root.addEventListener("click", (e) => this.handleClick(e));
  }

  async fetchInitialData() {
    try {
      this.courses = await window.api.getCourses();
    } catch (err) {
      console.error("Failed to load courses:", err);
      this.renderError("Could not load courses. Please refresh the page.");
    }
  }

  async handleRoute() {
    const hash = window.location.hash.slice(1) || "home";
    this.currentRoute = hash;

    if (hash === "home" || hash === "") {
      await this.renderHome();
    } else if (hash.startsWith("course/")) {
      const slug = hash.split("/")[1];
      await this.renderCourse(slug);
    } else if (hash.startsWith("lesson/")) {
      const lessonId = hash.split("/")[1];
      await this.renderLesson(lessonId);
    } else {
      this.renderHome();
    }
  }

  handleClick(e) {
    const btn = e.target.closest("[data-action]");
    if (!btn) return;

    const action = btn.dataset.action;
    if (action === "start-course") {
      const card = btn.closest("[data-course-id]");
      if (card) {
        window.location.hash = `course/${card.dataset.courseId}`;
      }
    } else if (action === "start-lesson") {
      const lessonId = btn.dataset.lessonId;
      window.location.hash = `lesson/${lessonId}`;
    } else if (action === "mark-complete") {
      const lessonId = btn.dataset.lessonId;
      this.markLessonComplete(lessonId);
    } else if (action === "back") {
      window.history.back();
    }
  }

  // ========== RENDERERS ==========

  renderHome() {
    if (!this.courses.length) {
      this.root.innerHTML = `<p>No courses available yet.</p>`;
      return;
    }

    let html = `<h1>${t("home.title", window.api.language)}</h1><div class="course-grid">`;
    for (const course of this.courses) {
      const title = course.title[window.api.language] || Object.values(course.title)[0];
      const desc = course.description[window.api.language] || Object.values(course.description)[0];
      html += `
        <article class="course-card" tabindex="0" data-course-id="${course.id}">
          <div class="icon">${course.icon || "📚"}</div>
          <h2>${title}</h2>
          <p>${desc}</p>
          <div class="meta">
            ${course.lesson_count} lessons • ~${course.estimated_minutes} min
          </div>
          <button class="btn" data-action="start-course">${t("actions.start", window.api.language)}</button>
        </article>
      `;
    }
    html += `</div>`;
    this.root.innerHTML = html;
    this.announcer.announce(`Loaded ${this.courses.length} courses`);
  }

  async renderCourse(courseSlug) {
    try {
      const course = await window.api.getCourse(courseSlug);
      this.renderCourseDetail(course);
    } catch (err) {
      this.renderError(err.message);
    }
  }

  renderCourseDetail(course) {
    const title = course.title[window.api.language] || Object.values(course.title)[0];
    const lessons = course.lessons || [];

    let html = `
      <div class="lesson-actions">
        <button class="btn btn-secondary" data-action="back" aria-label="${t("actions.back", window.api.language)}">
          ← ${t("actions.back", window.api.language)}
        </button>
      </div>
      <article class="lesson-content">
        <h1>${title}</h1>
        <p>${course.description[window.api.language] || ""}</p>
        <p><strong>${lessons.length} lessons</strong> • Estimated: ${course.estimated_minutes} minutes</p>
        <h2>${t("course.lessons", window.api.language)}</h2>
        <ul class="lesson-list">
    `;

    for (const lesson of lessons) {
      const ltitle = lesson.title[window.api.language] || Object.values(lesson.title)[0];
      const status = lesson.is_completed ? "✅" : "⬜";
      html += `
        <li class="lesson-item" style="margin: 1rem 0;">
          <button class="btn btn-secondary" data-action="start-lesson" data-lesson-id="${lesson.id}" style="width: 100%; text-align: left;">
            <span style="margin-right: 0.5rem;">${status}</span>
            <span>${ltitle}</span>
            <span style="margin-left: auto; opacity: 0.7;">${lesson.estimated_minutes} min</span>
          </button>
        </li>
      `;
    }

    html += `</ul></article>`;
    this.root.innerHTML = html;
    this.announcer.announce(`Course: ${title}`);
  }

  async renderLesson(lessonId) {
    try {
      const lesson = await window.api.getLesson(lessonId);
      this.renderLessonContent(lesson);
    } catch (err) {
      this.renderError(err.message);
    }
  }

  renderLessonContent(lesson) {
    const title = lesson.title[window.api.language] || Object.values(lesson.title)[0];
    const content = lesson.content || {};
    const isCompleted = lesson.is_completed;

    // Extract layout based on lesson type
    let body = "";
    let interactiveArea = "";
    let quizHtml = "";

    if (lesson.lesson_type === "text" || lesson.lesson_type === "interactive") {
      body = content.body || content.text || "";
      if (content.image) {
        body += `<img src="${content.image}" alt="" />`;
      }
      if (content.highlights) {
        for (const h of content.highlights) {
          body = body.replace(new RegExp(h, "gi"), match => `<span class="highlight">${match}</span>`);
        }
      }
      if (lesson.lesson_type === "interactive" && content.interactive_elements) {
        interactiveArea = `<div class="interactive-area" role="region" aria-label="${t("lesson.interactive", window.api.language)}">
          <p>${t("lesson.interactive_hint", window.api.language)}</p>
        </div>`;
      }
    } else if (lesson.lesson_type === "video") {
      if (content.video_url) {
        body = `<video controls src="${content.video_url}" style="max-width: 100%;"></video>`;
      }
    }

    // Quiz rendering
    if (lesson.lesson_type === "quiz" && content.quiz) {
      quizHtml = `<div class="quiz" role="form" aria-label="${t("lesson.quiz", window.api.language)}"><h3>${t("lesson.quiz", window.api.language)}</h3>`;
      for (const q of content.quiz) {
        quizHtml += `<div class="question"><p>${q.question}</p><ul class="choices">`;
        q.choices.forEach((choice, i) => {
          quizHtml += `
            <li class="choice">
              <label>
                <input type="radio" name="q-${q.question}" value="${i}">
                ${choice}
              </label>
            </li>`;
        });
        quizHtml += `</ul></div>`;
      }
      quizHtml += `<button class="btn" data-action="submit-quiz">${t("actions.submit", window.api.language)}</button></div>`;
    }

    const html = `
      <div class="lesson-actions">
        <button class="btn btn-secondary" data-action="back" aria-label="${t("actions.back", window.api.language)}">
          ← ${t("actions.back", window.api.language)}
        </button>
      </div>
      <article class="lesson-content" role="article" aria-labelledby="lesson-title">
        <h1 id="lesson-title">${title}</h1>
        <div class="lesson-body">${body}</div>
        ${interactiveArea}
        ${quizHtml}
        <div class="lesson-actions">
          <button class="btn ${isCompleted ? 'btn-secondary' : ''}" data-action="mark-complete" data-lesson-id="${lesson.id}">
            ${isCompleted ? "✔ Completed" : "Mark as Complete"}
          </button>
        </div>
      </article>
    `;

    this.root.innerHTML = html;
    this.speak(`Lesson: ${title}. ${body.slice(0, 200)}...`);

    // Setup quiz submit if present
    const quizBtn = this.root.querySelector('[data-action="submit-quiz"]');
    if (quizBtn) {
      quizBtn.addEventListener("click", () => this.submitQuiz(lesson.id));
    }
  }

  renderError(message) {
    this.root.innerHTML = `
      <div class="error" role="alert">
        <h2>Error</h2>
        <p>${message}</p>
        <button class="btn" onclick="window.location.reload()">${t("actions.retry", window.api.language)}</button>
      </div>
    `;
  }

  // ========== ACTIONS ==========

  async markLessonComplete(lessonId) {
    try {
      await window.api.updateLessonProgress(lessonId, "completed");
      this.announcer.announce("Lesson completed!");
      // Re-render current view
      await this.handleRoute();
      this.speak("Great job! You've completed this lesson.");
    } catch (err) {
      console.error("Failed to mark complete:", err);
      alert("Could not save progress");
    }
  }

  async submitQuiz(lessonId) {
    // Gather answers
    const inputs = this.root.querySelectorAll('[name^="q-"]');
    const answers = {};
    for (const input of inputs) {
      answers[input.name] = input.value;
    }
    try {
      await window.api.updateLessonProgress(lessonId, "completed", { quiz_answers: answers });
      this.announcer.announce("Quiz submitted!");
      await this.handleRoute();
    } catch (err) {
      alert("Could not submit quiz");
    }
  }

  // ========== UI UTILITIES ==========

  cycleLanguage() {
    const langs = ["en", "es", "fr", "pt"];
    const currentIdx = langs.indexOf(window.api.language);
    const nextLang = langs[(currentIdx + 1) % langs.length];
    window.api.setLanguage(nextLang);
    document.getElementById("lang-toggle").textContent = `🌐 ${this.getLangDisplay(nextLang)}`;
    localStorage.setItem("dlb_language", nextLang);
    // Refresh view
    this.handleRoute();
  }

  cycleTextSize() {
    const current = parseInt(getComputedStyle(document.documentElement).getPropertyValue("--font-size-base"));
    const sizes = [16, 18, 20, 22];
    const nextIdx = (sizes.indexOf(current) + 1) % sizes.length;
    const nextSize = sizes[nextIdx];
    document.documentElement.style.setProperty("--font-size-base", nextSize + "px");
    localStorage.setItem("dlb_font_size", nextSize);
  }

  toggleTTS() {
    this.ttsEnabled = !this.ttsEnabled;
    localStorage.setItem("dlb_tts", this.ttsEnabled);
    this.updateTTSButton();
    if (!this.ttsEnabled) {
      this.synth.cancel();
    }
  }

  updateTTSButton() {
    const btn = document.getElementById("tts-toggle");
    if (this.ttsEnabled) {
      btn.textContent = "🔊";
      btn.classList.add("btn-primary");
      btn.classList.remove("btn-secondary");
    } else {
      btn.textContent = "🔈";
      btn.classList.remove("btn-primary");
      btn.classList.add("btn-secondary");
    }
  }

  speak(text) {
    if (!this.ttsEnabled || !this.synth) return;
    this.synth.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    if (this.ttsVoice) utter.voice = this.ttsVoice;
    utter.rate = 0.9;
    this.synth.speak(utter);
  }
}

// Simple translation function (reads from i18n JSON)
async function loadTranslations() {
  const lang = window.api.language;
  try {
    const res = await fetch(`/static/i18n/${lang}.json`);
    if (!res.ok) throw new Error("Not found");
    return await res.json();
  } catch {
    // Fallback to English
    const res = await fetch("/static/i18n/en.json");
    return res.ok ? await res.json() : {};
  }
}

function t(key, lang = "en") {
  // This should be populated from loaded i18n JSON
  // For now, return key as fallback or define static map
  const static = {
    en: {
      "home.title": "Available Courses",
      "actions.start": "Start Course",
      "actions.back": "Back",
      "actions.submit": "Submit",
      "actions.retry": "Retry",
      "course.lessons": "Lessons",
      "lesson.interactive": "Interactive Section",
      "lesson.interactive_hint": "Follow the instructions to interact with the elements.",
      "lesson.quiz": "Quiz",
    },
    es: {
      "home.title": "Cursos Disponibles",
      "actions.start": "Comenzar",
      "actions.back": "Atrás",
      "actions.submit": "Enviar",
      "actions.retry": "Reintentar",
      "course.lessons": "Lecciones",
      "lesson.interactive": "Sección Interactiva",
      "lesson.interactive_hint": "Sigue las instrucciones para interactuar con los elementos.",
      "lesson.quiz": "Cuestionario",
    },
  };
  return (static[lang] && static[lang][key]) || key;
}

// Initialize app when DOM ready
document.addEventListener("DOMContentLoaded", async () => {
  window.app = new App();
  await window.app.init();
});
