const overlayStatePath = "../../data/overlay_state.json";

let latestOverlayState = null;
let displayedStatsMode = "currentSession";
let remainingSecondsForMode = 20;
let lastGameName = "";
let isStatsTransitionRunning = false;
let activePanelName = "primary";
let lastAppliedLogoSource = "";

function getFontFamilyForGame(gameName) {
	if (gameName === "Overwatch") {
		return '"Futura Regular", sans-serif';
	}
	if (gameName === "Valorant") {
		return '"Valorant Font", sans-serif';
	}
	return "sans-serif";
}

function formatRatio(value) {
	const numericValue = Number(value ?? 0);
	if (Number.isNaN(numericValue)) {
		return "0.00";
	}
	return numericValue.toFixed(2);
}

function resetModeRotation() {
	displayedStatsMode = "currentSession";
	remainingSecondsForMode = 20;
}

function getPanelElements(panelName) {
	return {
		container: document.getElementById(panelName === "primary" ? "stats-panel-primary" : "stats-panel-secondary"),
		modeLabel: document.getElementById(panelName === "primary" ? "primary-mode-label" : "secondary-mode-label"),
		winsValue: document.getElementById(panelName === "primary" ? "primary-wins-value" : "secondary-wins-value"),
		lossesValue: document.getElementById(panelName === "primary" ? "primary-losses-value" : "secondary-losses-value"),
		drawsValue: document.getElementById(panelName === "primary" ? "primary-draws-value" : "secondary-draws-value"),
		ratioValue: document.getElementById(panelName === "primary" ? "primary-ratio-value" : "secondary-ratio-value"),
	};
}

function getStatsForMode(statsMode) {
	if (!latestOverlayState || !latestOverlayState.stats) {
		return null;
	}
	return latestOverlayState.stats[statsMode] || latestOverlayState.stats.currentSession;
}

function setPanelContent(panelName, statsMode) {
	const panelElements = getPanelElements(panelName);
	const statsValues = getStatsForMode(statsMode);
	if (!panelElements || !statsValues) {
		return;
	}

	panelElements.modeLabel.textContent = statsMode === "currentSession" ? "Current Session" : "Total";
	panelElements.winsValue.textContent = `W: ${statsValues.wins ?? 0}`;
	panelElements.lossesValue.textContent = `L: ${statsValues.losses ?? 0}`;
	panelElements.drawsValue.textContent = `D: ${statsValues.draws ?? 0}`;
	panelElements.ratioValue.textContent = `R: ${formatRatio(statsValues.ratio)}`;
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

function applyStatsToUi(forceRefresh = false) {
	if (!latestOverlayState || !latestOverlayState.stats) {
		return;
	}

	const activeGame = latestOverlayState.activeGame || "Overwatch";
    const statsOpacity = latestOverlayState.opacities?.stats ?? latestOverlayState.opacity ?? 1;

	document.body.style.fontFamily = getFontFamilyForGame(activeGame);
	document.body.style.opacity = String(statsOpacity);

	const logoElement = document.getElementById("game-logo");
	const preferredLogoSource = latestOverlayState.assets?.logoDataUri || latestOverlayState.assets?.logo || lastAppliedLogoSource || "";
	if (preferredLogoSource && preferredLogoSource !== lastAppliedLogoSource) {
		logoElement.src = preferredLogoSource;
		lastAppliedLogoSource = preferredLogoSource;
	}
	logoElement.alt = `${activeGame} Logo`;

	if (forceRefresh) {
		setPanelContent("primary", displayedStatsMode);
		setPanelContent("secondary", displayedStatsMode);
		positionPanelsForStaticView();
		return;
	}

	if (isStatsTransitionRunning) {
		return;
	}

	setPanelContent(activePanelName, displayedStatsMode);
}

function animateStatsModeTransition(nextStatsMode) {
	if (isStatsTransitionRunning) {
		return;
	}

	isStatsTransitionRunning = true;
	const currentPanelName = activePanelName;
	const nextPanelName = currentPanelName === "primary" ? "secondary" : "primary";

	const currentPanel = getPanelElements(currentPanelName).container;
	const nextPanel = getPanelElements(nextPanelName).container;

	setPanelContent(nextPanelName, nextStatsMode);
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
		displayedStatsMode = nextStatsMode;
		isStatsTransitionRunning = false;
		applyStatsToUi(false);
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
		const gameNameChanged = overlayState.activeGame !== lastGameName;
		latestOverlayState = overlayState;

		if (gameNameChanged) {
			lastGameName = overlayState.activeGame || "";
			resetModeRotation();
			activePanelName = "primary";
			applyStatsToUi(true);
			return;
		}

		applyStatsToUi(false);
	} catch (error) {
		return;
	}
}

function tickStatsModeRotation() {
	remainingSecondsForMode -= 1;
	if (remainingSecondsForMode > 0) {
		return;
	}

	if (displayedStatsMode === "currentSession") {
		remainingSecondsForMode = 10;
		animateStatsModeTransition("total");
	} else {
		remainingSecondsForMode = 20;
		animateStatsModeTransition("currentSession");
	}
}

refreshOverlayState();
setInterval(refreshOverlayState, 1000);
setInterval(tickStatsModeRotation, 1000);
