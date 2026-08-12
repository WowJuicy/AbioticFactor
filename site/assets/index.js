
(function () {
  const input = document.getElementById("filter");
  const cards = Array.from(document.querySelectorAll(".item-card"));
  if (!input) return;

  input.addEventListener("input", () => {
    const q = input.value.trim().toLowerCase();
    cards.forEach((card) => {
      const name = (card.dataset.name || "").toLowerCase();
      card.classList.toggle("hidden", q && !name.includes(q));
    });
  });
})();
