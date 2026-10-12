/**
 * Women's Safety Device Dashboard - Client Interactions
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Lightbox setup
  const lightbox = document.getElementById("photo-lightbox");
  const lightboxImg = document.getElementById("lightbox-img");
  const lightboxClose = document.getElementById("lightbox-close");

  if (lightbox && lightboxImg) {
    document.querySelectorAll(".photo-item img").forEach((img) => {
      img.addEventListener("click", () => {
        lightboxImg.src = img.src;
        lightboxImg.alt = img.alt || "Alert Photo";
        lightbox.classList.add("active");
        lightbox.setAttribute("aria-hidden", "false");
      });
    });

    const closeLightbox = () => {
      lightbox.classList.remove("active");
      lightbox.setAttribute("aria-hidden", "true");
      lightboxImg.src = "";
    };

    if (lightboxClose) {
      lightboxClose.addEventListener("click", closeLightbox);
    }

    lightbox.addEventListener("click", (e) => {
      if (e.target === lightbox) {
        closeLightbox();
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && lightbox.classList.contains("active")) {
        closeLightbox();
      }
    });
  }

  // 2. Audio playback exclusive play (pause other audios when one begins)
  const audios = document.querySelectorAll("audio");
  audios.forEach((audio) => {
    audio.addEventListener("play", () => {
      audios.forEach((otherAudio) => {
        if (otherAudio !== audio && !otherAudio.paused) {
          otherAudio.pause();
        }
      });
    });
  });

  // 3. Confirm Delete Prompts
  document.querySelectorAll(".form-delete-alert").forEach((form) => {
    form.addEventListener("submit", (e) => {
      const alertId = form.getAttribute("data-alert-id") || "";
      const confirmed = window.confirm(
        `Are you sure you want to permanently delete Emergency Alert #${alertId} and all of its recorded photos and audio files?`
      );
      if (!confirmed) {
        e.preventDefault();
      }
    });
  });

  // 4. Auto-dismiss flash notifications after 6 seconds
  setTimeout(() => {
    document.querySelectorAll(".flash-message").forEach((msg) => {
      msg.style.transition = "opacity 0.5s ease";
      msg.style.opacity = "0";
      setTimeout(() => msg.remove(), 500);
    });
  }, 6000);
});
