document.addEventListener("DOMContentLoaded", function () {
  const legsContainer = document.getElementById("legs");
  const template = document.getElementById("leg-template");
  const addLegBtn = document.getElementById("add-leg");
  const betTypeSelect = document.getElementById("bet-type-select");
  const isGroupCheckbox = document.getElementById("is-group-bet");

  function addLeg() {
    const clone = template.content.cloneNode(true);
    clone.querySelector(".remove-leg").addEventListener("click", function (e) {
      e.target.closest(".leg-row").remove();
    });
    legsContainer.appendChild(clone);
  }

  addLegBtn.addEventListener("click", addLeg);
  addLeg(); // start every new bet with one leg row

  betTypeSelect.addEventListener("change", function () {
    const selected = betTypeSelect.options[betTypeSelect.selectedIndex];
    isGroupCheckbox.checked = selected.dataset.defaultGroup === "true";
  });
  // Apply the default for whatever bet type is selected on page load.
  betTypeSelect.dispatchEvent(new Event("change"));
});
