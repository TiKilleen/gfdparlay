document.addEventListener("DOMContentLoaded", function () {
  const legsContainer = document.getElementById("legs");
  const template = document.getElementById("leg-template");
  const addLegBtn = document.getElementById("add-leg");
  const betTypeSelect = document.getElementById("bet-type-select");
  const isGroupCheckbox = document.getElementById("is-group-bet");

  function addLeg(prefill) {
    const clone = template.content.cloneNode(true);
    const row = clone.querySelector(".leg-row");
    row.querySelector(".remove-leg").addEventListener("click", function (e) {
      e.target.closest(".leg-row").remove();
    });
    if (prefill) {
      row.querySelector('[name="leg_bettor_id"]').value = prefill.bettor_id;
      row.querySelector('[name="leg_player_name"]').value = prefill.player_name || "";
      row.querySelector('[name="leg_prop_category"]').value = prefill.prop_category;
      row.querySelector('[name="leg_description"]').value = prefill.description;
      row.querySelector('[name="leg_odds"]').value = prefill.odds;
    }
    row.querySelectorAll("[data-autocomplete]").forEach(attachAutocomplete);
    legsContainer.appendChild(clone);
  }

  addLegBtn.addEventListener("click", function () {
    addLeg();
  });

  const existingLegs = window.EXISTING_LEGS;
  if (existingLegs && existingLegs.length) {
    existingLegs.forEach(addLeg);
  } else {
    addLeg(); // start a brand-new bet with one empty leg row
  }

  betTypeSelect.addEventListener("change", function () {
    const selected = betTypeSelect.options[betTypeSelect.selectedIndex];
    isGroupCheckbox.checked = selected.dataset.defaultGroup === "true";
  });
  // Only apply the bet-type default on a fresh bet -- an edit form should
  // keep whatever is_group_bet was actually saved, not silently flip it
  // back to the bet type's default the moment the page loads.
  if (!existingLegs) {
    betTypeSelect.dispatchEvent(new Event("change"));
  }
});

// Native <datalist> suggestions don't render on iOS Safari, which is the
// primary device this form gets used on (game-day, one-handed) -- so
// autocomplete is hand-rolled here instead of relying on the browser.
function attachAutocomplete(input) {
  const options = (window.AUTOCOMPLETE_OPTIONS || {})[input.dataset.autocomplete] || [];
  const list = input.parentElement.querySelector(".autocomplete-list");

  function render(matches) {
    list.innerHTML = "";
    if (!matches.length) {
      list.hidden = true;
      return;
    }
    matches.slice(0, 8).forEach(function (name) {
      const item = document.createElement("div");
      item.className = "autocomplete-item";
      item.textContent = name;
      item.addEventListener("mousedown", function (e) {
        e.preventDefault(); // fires before input's blur would hide the list
        input.value = name;
        list.hidden = true;
      });
      list.appendChild(item);
    });
    list.hidden = false;
  }

  input.addEventListener("input", function () {
    const query = input.value.trim().toLowerCase();
    if (!query) {
      list.hidden = true;
      return;
    }
    render(options.filter((name) => name.toLowerCase().includes(query)));
  });

  input.addEventListener("blur", function () {
    setTimeout(function () {
      list.hidden = true;
    }, 150);
  });
}
