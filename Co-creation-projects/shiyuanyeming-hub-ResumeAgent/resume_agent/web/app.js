const tabs = document.querySelector("#primary-tabs");
const panels = [...document.querySelectorAll("[data-panel]")];

function selectTab(name) {
  for (const button of tabs.querySelectorAll("button")) {
    button.setAttribute("aria-selected", String(button.dataset.tab === name));
  }
  for (const panel of panels) {
    panel.hidden = panel.dataset.panel !== name;
  }
  document.querySelector("#chat-composer").hidden = name !== "chat";
}

tabs.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-tab]");
  if (button) selectTab(button.dataset.tab);
});

document.querySelector("#settings-button").addEventListener("click", () => {
  document.querySelector("#settings-dialog").showModal();
});
