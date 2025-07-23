document.addEventListener("DOMContentLoaded", () => {
  const transactionForm = document.getElementById("transactionForm");
  if (!transactionForm) {
    console.error("The element #transactionForm was not found in your HTML.");
    return;
  }

  transactionForm.addEventListener("submit", async function (e) {
    e.preventDefault();

    // A dedicated element for showing messages is better than alert()
    const messageEl = document.getElementById("transaction-message");
    if (!messageEl) {
      console.error("The element #transaction-message was not found in your HTML.");
      return;
    }
    // Clear previous messages
    messageEl.textContent = "";

    // --- Form Data & Validation ---
    const selectedType = document.querySelector('input[name="type"]:checked');
    const amount = document.getElementById("amount").value;
    const category = document.getElementById("category").value;
    const date = document.getElementById("date").value;

    if (!selectedType) {
      messageEl.textContent = "Please select a transaction type (Income or Expense).";
      messageEl.style.color = "red";
      return;
    }

    if (!amount || parseFloat(amount) <= 0) {
      messageEl.textContent = "Please enter a valid positive amount.";
      messageEl.style.color = "red";
      return;
    }

    if (!category.trim()) {
      messageEl.textContent = "Please select a category.";
      messageEl.style.color = "red";
      return;
    }

    if (!date) {
      messageEl.textContent = "Please select a date.";
      messageEl.style.color = "red";
      return;
    }

    const data = {
      type: selectedType.value,
      amount: parseFloat(amount),
      category: category,
      date: date,
      description: document.getElementById("description").value,
    };

    try {
      const response = await fetch("/transaction", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      // --- Enhanced Debugging ---
      // These logs will help us see exactly what the server is sending back.
      // Please open your browser's Developer Tools (F12), go to the "Console" tab,
      // and check the output after submitting the form.
      console.log("--- Server Response ---");
      console.log("Status:", response.status, response.statusText);
      console.log("OK:", response.ok);
      console.log("Redirected:", response.redirected);
      console.log("URL:", response.url);
      const responseText = await response.clone().text(); // Clone to read body without consuming it
      console.log("Body (raw text):", responseText);
      console.log("-----------------------");

      // If the server redirected (e.g., to a login page due to an expired session),
      // this indicates an authentication issue. Let's navigate to the new page.
      if (response.redirected) {
        window.location.href = response.url;
        return;
      }

      // Try to parse the response as JSON. It might fail if the server
      // sent an HTML error page instead of a JSON error object.
      const result = await response.json().catch(() => null);

      if (!response.ok) {
        const errorMessage = result?.message || `Error: ${response.statusText}`;
        messageEl.textContent = errorMessage;
        messageEl.style.color = "red";
        return;
      }

      messageEl.textContent = result.message;
      messageEl.style.color = "green";

      transactionForm.reset();
      setTimeout(() => (window.location.href = "/dashboard"), 1500);
    } catch (err) {
      messageEl.textContent = "An error occurred. Please check the console for details.";
      messageEl.style.color = "red";
      console.error(err);
    }
  });
});
