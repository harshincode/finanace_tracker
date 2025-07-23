document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("signupForm");
  const message = document.getElementById("message");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value.trim();

    const res = await fetch("/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();
    message.innerText = data.message;
    message.style.color = res.ok ? "green" : "red";

    if (res.ok) {
      setTimeout(() => {
        window.location.href = "/";
      }, 1000);
    }
  });
});
