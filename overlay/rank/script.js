const overlayStatePath = "../../data/overlay_state.json";

let rankEntries = [];
let displayedRankEntryIndex = 0;
let lastGameName = "";
let latestOverlayState = null;
let activePanelName = "primary";
let isRankTransitionRunning = false;

function getFontFamilyForGame(gameName) {
	if (gameName === "Overwatch") {
		return '"Futura Regular", sans-serif';
	}
	if (gameName === "Valorant") {
		return '"Valorant Font", sans-serif';
	}
	return "sans-serif";
}

function getPanelElements(panelName) {
	return {
		container: document.getElementById(panelName === "primary" ? "rank-panel-primary" : "rank-panel-secondary"),
		label: document.getElementById(panelName === "primary" ? "primary-rank-label" : "secondary-rank-label"),
		icon: document.getElementById(panelName === "primary" ? "primary-rank-icon" : "secondary-rank-icon"),
		text: document.getElementById(panelName === "primary" ? "primary-rank-text" : "secondary-rank-text"),
	};
}

function getDisplayedRankEntry() {
	if (!rankEntries.length) {
		return null;
	}
	return rankEntries[displayedRankEntryIndex] || rankEntries[0];
}

function setPanelContent(panelName, rankEntry) {
	const panelElements = getPanelElements(panelName);
	const isMultiCategoryEntry = Boolean(rankEntry && rankEntry.category);

	if (!rankEntry) {
		panelElements.label.textContent = "Unranked";
		panelElements.icon.style.display = "none";
		panelElements.icon.removeAttribute("src");
		panelElements.icon.alt = "Unranked";
		panelElements.text.style.display = "none";
		panelElements.text.textContent = "";
		return;
	}

	panelElements.text.style.display = "none";
	panelElements.text.textContent = "";
	panelElements.icon.style.display = "block";
	const preferredIconSource = rankEntry.imageDataUri || rankEntry.image || panelElements.icon.dataset.cachedSource || "";
	if (preferredIconSource && panelElements.icon.dataset.cachedSource !== preferredIconSource) {
		panelElements.icon.src = preferredIconSource;
		panelElements.icon.dataset.cachedSource = preferredIconSource;
	}
	panelElements.icon.alt = rankEntry.rank;

	if (isMultiCategoryEntry) {
		panelElements.label.textContent = `${rankEntry.category}:`;
	} else {
		panelElements.label.textContent = "Rank:";
	}
}

function positionPanelsForStaticView() {
	const primaryPanel = getPanelElements("primary").container;
	const secondaryPanel = getPanelElements("secondary").container;
	if (activePanelName === "primary") {
		primaryPanel.style.transform = "translateY(0%)";
		secondaryPanel.style.transform = "translateY(-100%)";
	} else {
		secondaryPanel.style.transform = "translateY(0%)";
		primaryPanel.style.transform = "translateY(-100%)";
	}
}

function applyRankEntry(overlayState, forceRefresh = false) {
	const rankOpacity = overlayState.opacities?.rank ?? overlayState.opacity ?? 1;
	document.body.style.fontFamily = getFontFamilyForGame(overlayState.activeGame || "Overwatch");
	document.body.style.opacity = String(rankOpacity);

	if (forceRefresh) {
		setPanelContent("primary", getDisplayedRankEntry());
		setPanelContent("secondary", getDisplayedRankEntry());
		positionPanelsForStaticView();
		return;
	}

	if (isRankTransitionRunning) {
		return;
	}

	setPanelContent(activePanelName, getDisplayedRankEntry());
}

function animateRankTransition() {
	if (isRankTransitionRunning) {
		return;
	}

	isRankTransitionRunning = true;
	const currentPanelName = activePanelName;
	const nextPanelName = currentPanelName === "primary" ? "secondary" : "primary";
	const currentPanel = getPanelElements(currentPanelName).container;
	const nextPanel = getPanelElements(nextPanelName).container;

	setPanelContent(nextPanelName, getDisplayedRankEntry());
	nextPanel.style.transform = "translateY(-100%)";

	const onTransitionEnd = (event) => {
		if (event.propertyName !== "transform") {
			return;
		}
		nextPanel.removeEventListener("transitionend", onTransitionEnd);

		const currentPanelTransitionValue = currentPanel.style.transition;
		currentPanel.style.transition = "none";
		currentPanel.style.transform = "translateY(-100%)";
		void currentPanel.offsetHeight;
		currentPanel.style.transition = currentPanelTransitionValue;

		activePanelName = nextPanelName;
		isRankTransitionRunning = false;
		if (latestOverlayState) {
			applyRankEntry(latestOverlayState, false);
		}
	};
	nextPanel.addEventListener("transitionend", onTransitionEnd);

	requestAnimationFrame(() => {
		requestAnimationFrame(() => {
			currentPanel.style.transform = "translateY(100%)";
			nextPanel.style.transform = "translateY(0%)";
		});
	});
}

async function refreshOverlayState() {
	try {
		const response = await fetch(`${overlayStatePath}?cacheBust=${Date.now()}`, { cache: "no-store" });
		if (!response.ok) {
			return;
		}

		const overlayState = await response.json();
		latestOverlayState = overlayState;
		const activeGame = overlayState.activeGame || "";
		const gameChanged = activeGame !== lastGameName;
		rankEntries = Array.isArray(overlayState.rank?.entries) ? overlayState.rank.entries : [];
		if (displayedRankEntryIndex >= rankEntries.length) {
			displayedRankEntryIndex = 0;
		}

		if (gameChanged) {
			lastGameName = activeGame;
			displayedRankEntryIndex = 0;
			activePanelName = "primary";
			applyRankEntry(overlayState, true);
			return;
		}

		applyRankEntry(overlayState, false);
	} catch (error) {
		return;
	}
}

function cycleRankEntry() {
	if (rankEntries.length <= 1) {
		return;
	}
	displayedRankEntryIndex += 1;
	if (displayedRankEntryIndex >= rankEntries.length) {
		displayedRankEntryIndex = 0;
	}
	animateRankTransition();
}

refreshOverlayState();
setInterval(refreshOverlayState, 1000);
setInterval(cycleRankEntry, 5000);
