document.addEventListener("DOMContentLoaded", () => {
  const transactionForm = document.getElementById("transactionForm");
  if (!transactionForm) {
    console.error("The element #transactionForm was not found in your HTML.");
    return;
  }

  // Set today's date as default
  const dateInput = document.getElementById("date");
  if (dateInput) {
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
  }

  transactionForm.addEventListener("submit", async function (e) {
    e.preventDefault();

    // A dedicated element for showing messages is better than alert()
    const messageEl = document.getElementById("transaction-message");
    if (!messageEl) {
      console.error("The element #transaction-message was not found in your HTML.");
      return;
    }
    
    // Function to show message
    const showMessage = (text, isError = false) => {
      messageEl.textContent = text;
      messageEl.style.display = "block";
      messageEl.style.color = isError ? "red" : "green";
      messageEl.style.backgroundColor = isError ? "#ffebee" : "#e8f5e8";
      messageEl.style.border = isError ? "1px solid #f44336" : "1px solid #4caf50";
    };

    // Clear previous messages
    messageEl.style.display = "none";
    messageEl.textContent = "";

    // --- Form Data & Validation ---
    const selectedType = document.querySelector('input[name="type"]:checked');
    const amount = document.getElementById("amount").value;
    const category = document.getElementById("category").value;
    const date = document.getElementById("date").value;

    if (!selectedType) {
      showMessage("Please select a transaction type (Income or Expense).", true);
      return;
    }

    if (!amount || parseFloat(amount) <= 0) {
      showMessage("Please enter a valid positive amount.", true);
      return;
    }

    if (!category.trim()) {
      showMessage("Please select a category.", true);
      return;
    }

    if (!date) {
      showMessage("Please select a date.", true);
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
      // Show loading message
      showMessage("Processing transaction...", false);
      
      const response = await fetch("/transaction", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      // --- Enhanced Debugging ---
      console.log("--- Transaction Submission Debug Info ---");
      console.log("Request data:", data);
      console.log("Status:", response.status, response.statusText);
      console.log("OK:", response.ok);
      console.log("Redirected:", response.redirected);
      console.log("URL:", response.url);
      const responseText = await response.clone().text();
      console.log("Body (raw text):", responseText);
      console.log("----------------------------------------");

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
        showMessage(errorMessage, true);
        return;
      }

      showMessage(result.message || "Transaction added successfully!");
      transactionForm.reset();
      
      // Redirect to dashboard after a short delay
      setTimeout(() => {
        window.location.href = "/dashboard";
      }, 1500);
      
    } catch (err) {
      showMessage("An error occurred. Please check the console for details.", true);
      console.error(err);
    }
  });
});
