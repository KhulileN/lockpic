/**
 * Digital Literacy Bridge - API Client
 *
 * Simple wrapper around fetch() for the DLB API.
 * Handles base URL, JSON serialization, and error handling.
 */

const API_BASE = "/api/v1";

/**
 * DLB API Client
 */
class APIClient {
  constructor() {
    this.baseUrl = API_BASE;
    this.language = this.getPreferredLanguage();
    this.userId = null; // Populated from cookie on demand
  }

  /**
   * Get preferred language from browser or localStorage.
   * Falls back to 'en'.
   */
  getPreferredLanguage() {
    const saved = localStorage.getItem("dlb_language");
    if (saved) return saved;
    const browserLang = navigator.language || navigator.userLanguage || "en";
    return browserLang.split("-")[0]; // e.g., "en-US" -> "en"
  }

  /**
   * Set preferred language and persist.
   */
  setLanguage(lang) {
    this.language = lang;
    localStorage.setItem("dlb_language", lang);
  }

  /**
   * Build query string with language and other params.
   */
  buildParams(params = {}) {
    const p = new URLSearchParams();
    if (!params.language) {
      p.set("language", this.language);
    }
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) p.set(k, v);
    });
    const qs = p.toString();
    return qs ? `?${qs}` : "";
  }

  /**
   * Generic fetch wrapper.
   */
  async fetch(url, options = {}) {
    const fullUrl = this.baseUrl + url;
    const opts = {
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include", // include cookies for anonymous user
      ...options,
    };
    if (opts.body && typeof opts.body === "object") {
      opts.body = JSON.stringify(opts.body);
    }
    try {
      const response = await fetch(fullUrl, opts);
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${response.status}: ${response.statusText}`);
      }
      // For 204 No Content, return null
      if (response.status === 204) return null;
      return await response.json();
    } catch (e) {
      console.error("API error:", e);
      throw e;
    }
  }

  // ---------- Courses ----------
  async getCourses(params = {}) {
    return this.fetch(`/courses${this.buildParams(params)}`);
  }

  async getCourse(slug, params = {}) {
    return this.fetch(`/courses/${encodeURIComponent(slug)}${this.buildParams(params)}`);
  }

  async createCourse(data) {
    return this.fetch("/courses", { method: "POST", body: data });
  }

  // ---------- Lessons ----------
  async getLesson(lessonId, params = {}) {
    return this.fetch(`/lessons/${encodeURIComponent(lessonId)}${this.buildParams(params)}`);
  }

  async createLesson(data) {
    return this.fetch("/lessons", { method: "POST", body: data });
  }

  // ---------- Progress ----------
  async getMyProgress() {
    return this.fetch("/progress/me");
  }

  async updateLessonProgress(lessonId, status, metadata = {}) {
    return this.fetch(
      `/progress/lessons/${encodeURIComponent(lessonId)}`,
      {
        method: "POST",
        body: { status, metadata },
      }
    );
  }

  // ---------- Content Loader ----------
  async listContentCourses() {
    return this.fetch("/content/courses");
  }

  // ---------- Auth / User ----------
  async getCurrentUser() {
    // User is set via cookie by dependency; we just need to trigger a request
    // or provide a /users/me endpoint. For now, assume progress endpoints
    // will fail if not authenticated; we treat that as anonymous.
    try {
      const data = await this.getMyProgress();
      // If this succeeds, we have a user.
      return { anonymous: true };
    } catch (e) {
      return null;
    }
  }
}

// Create singleton instance
window.api = new APIClient();
