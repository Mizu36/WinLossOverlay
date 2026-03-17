import tkinter
from tkinter import messagebox
from tkinter import ttk

import main


class StatsTrackerGui:
	def __init__(self, root_window, overlay_port=None):
		self.root_window = root_window
		self.overlay_port = overlay_port
		self.stats_source_url = ""
		self.rank_source_url = ""

		self.root_window.title("Win/Loss Overlay Tracker")
		self.root_window.geometry("800x900")
		self.root_window.minsize(800, 900)

		self.active_game_variable = tkinter.StringVar(value=main.current_game)
		self.stats_overlay_opacity_variable = tkinter.IntVar(value=int(main.settings.get("Stats Overlay Opacity", main.settings.get("Opacity", 100))))
		self.rank_overlay_opacity_variable = tkinter.IntVar(value=int(main.settings.get("Rank Overlay Opacity", main.settings.get("Opacity", 100))))
		self.rank_category_variable = tkinter.StringVar(value="")
		self.rank_value_variable = tkinter.StringVar(value="Unranked")

		self.session_wins_variable = tkinter.StringVar(value="0")
		self.session_losses_variable = tkinter.StringVar(value="0")
		self.session_draws_variable = tkinter.StringVar(value="0")

		self.hotkey_variables = {}
		self.hotkey_entries = {}
		self.hotkey_record_buttons = {}
		self.hotkey_status_variable = tkinter.StringVar(value="Hotkeys not registered yet.")
		self.is_recording_hotkey = False
		self.recording_hotkey_name = ""
		self.recording_original_hotkey_text = ""
		self.current_recording_modifiers = set()

		self.create_layout()
		self.refresh_all_display_values()
		self.register_hotkeys_for_runtime(show_message=False)
		self.root_window.protocol("WM_DELETE_WINDOW", self.handle_window_close)

	def create_layout(self):
		notebook = ttk.Notebook(self.root_window)
		notebook.pack(fill="both", expand=True, padx=12, pady=12)

		settings_tab_frame = ttk.Frame(notebook, padding=12)
		actions_tab_frame = ttk.Frame(notebook, padding=12)
		notebook.add(settings_tab_frame, text="Settings")
		notebook.add(actions_tab_frame, text="Actions")

		self.build_settings_tab(settings_tab_frame)
		self.build_actions_tab(actions_tab_frame)

	def build_settings_tab(self, parent_frame):
		active_game_frame = ttk.LabelFrame(parent_frame, text="Active Game", padding=12)
		active_game_frame.pack(fill="x", pady=(0, 10))

		available_games = sorted(main.saved_data.keys())
		self.active_game_combobox = ttk.Combobox(
			active_game_frame,
			textvariable=self.active_game_variable,
			values=available_games,
			state="readonly",
			width=28,
		)
		self.active_game_combobox.pack(anchor="w")
		self.active_game_combobox.bind("<<ComboboxSelected>>", self.on_active_game_changed)

		opacity_frame = ttk.LabelFrame(parent_frame, text="Overlay Opacity", padding=12)
		opacity_frame.pack(fill="x", pady=(0, 10))

		self.stats_opacity_label = ttk.Label(opacity_frame, text=f"Stats Opacity: {self.stats_overlay_opacity_variable.get()}%")
		self.stats_opacity_label.pack(anchor="w", pady=(0, 6))

		stats_opacity_slider = ttk.Scale(
			opacity_frame,
			from_=0,
			to=100,
			orient="horizontal",
			command=self.on_stats_opacity_slider_changed,
		)
		stats_opacity_slider.pack(fill="x", pady=(0, 8))
		stats_opacity_slider.set(self.stats_overlay_opacity_variable.get())

		self.rank_opacity_label = ttk.Label(opacity_frame, text=f"Rank Opacity: {self.rank_overlay_opacity_variable.get()}%")
		self.rank_opacity_label.pack(anchor="w", pady=(0, 6))

		rank_opacity_slider = ttk.Scale(
			opacity_frame,
			from_=0,
			to=100,
			orient="horizontal",
			command=self.on_rank_opacity_slider_changed,
		)
		rank_opacity_slider.pack(fill="x")
		rank_opacity_slider.set(self.rank_overlay_opacity_variable.get())

		hotkey_frame = ttk.LabelFrame(parent_frame, text="Hotkeys", padding=12)
		hotkey_frame.pack(fill="both", expand=True, pady=(0, 10))

		hotkey_field_names = [
			"Record Win",
			"Record Loss",
			"Record Draw",
			"Reset Current Stats",
			"Increase Rank",
			"Decrease Rank",
		]

		for row_index, hotkey_field_name in enumerate(hotkey_field_names):
			ttk.Label(hotkey_frame, text=hotkey_field_name).grid(row=row_index, column=0, sticky="w", padx=(0, 8), pady=3)
			hotkey_value = self.normalize_hotkey_text(main.settings.get("Hotkeys", {}).get(hotkey_field_name, ""))
			hotkey_value_variable = tkinter.StringVar(value=hotkey_value)
			self.hotkey_variables[hotkey_field_name] = hotkey_value_variable
			hotkey_entry = ttk.Entry(hotkey_frame, textvariable=hotkey_value_variable, width=28)
			hotkey_entry.grid(row=row_index, column=1, sticky="w", pady=3)
			self.hotkey_entries[hotkey_field_name] = hotkey_entry
			record_button = ttk.Button(
				hotkey_frame,
				text="Record",
				command=lambda current_hotkey_field_name=hotkey_field_name: self.start_hotkey_recording(current_hotkey_field_name),
			)
			record_button.grid(row=row_index, column=2, sticky="w", padx=(8, 0), pady=3)
			self.hotkey_record_buttons[hotkey_field_name] = record_button

		save_hotkeys_button = ttk.Button(hotkey_frame, text="Save Hotkeys", command=self.save_hotkeys)
		save_hotkeys_button.grid(row=len(hotkey_field_names), column=0, columnspan=3, sticky="w", pady=(10, 0))

		if self.overlay_port is not None:
			overlay_info_frame = ttk.LabelFrame(parent_frame, text="OBS Browser Source URLs", padding=12)
			overlay_info_frame.pack(fill="x")
			self.stats_source_url = f"http://127.0.0.1:{self.overlay_port}/overlay/stats/index.html"
			self.rank_source_url = f"http://127.0.0.1:{self.overlay_port}/overlay/rank/index.html"

			ttk.Label(overlay_info_frame, text="Stats Source").grid(row=0, column=0, sticky="w")
			stats_entry = ttk.Entry(overlay_info_frame, width=72)
			stats_entry.grid(row=1, column=0, sticky="ew", pady=(2, 6), padx=(0, 6))
			stats_entry.insert(0, self.stats_source_url)
			stats_entry.configure(state="readonly")
			ttk.Button(overlay_info_frame, text="Copy Stats URL", command=self.copy_stats_source_url).grid(row=1, column=1, sticky="ew")

			ttk.Label(overlay_info_frame, text="Rank Source").grid(row=2, column=0, sticky="w")
			rank_entry = ttk.Entry(overlay_info_frame, width=72)
			rank_entry.grid(row=3, column=0, sticky="ew", pady=(2, 6), padx=(0, 6))
			rank_entry.insert(0, self.rank_source_url)
			rank_entry.configure(state="readonly")
			ttk.Button(overlay_info_frame, text="Copy Rank URL", command=self.copy_rank_source_url).grid(row=3, column=1, sticky="ew")

			ttk.Button(overlay_info_frame, text="Copy Both URLs", command=self.copy_both_source_urls).grid(row=4, column=1, sticky="ew")
			overlay_info_frame.grid_columnconfigure(0, weight=1)

		hotkey_status_frame = ttk.LabelFrame(parent_frame, text="Hotkey Listener Status", padding=12)
		hotkey_status_frame.pack(fill="x")
		ttk.Label(hotkey_status_frame, textvariable=self.hotkey_status_variable).pack(anchor="w")

	def build_actions_tab(self, parent_frame):
		top_row_frame = ttk.Frame(parent_frame)
		top_row_frame.pack(fill="x")

		record_frame = ttk.LabelFrame(top_row_frame, text="Record Match Results", padding=12)
		record_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

		ttk.Button(record_frame, text="Record Win", command=self.handle_record_win).grid(row=0, column=0, padx=4, pady=4, sticky="ew")
		ttk.Button(record_frame, text="Record Loss", command=self.handle_record_loss).grid(row=0, column=1, padx=4, pady=4, sticky="ew")
		ttk.Button(record_frame, text="Record Draw", command=self.handle_record_draw).grid(row=0, column=2, padx=4, pady=4, sticky="ew")
		ttk.Button(record_frame, text="Reset Current Stats", command=self.handle_reset_current_stats).grid(row=1, column=0, columnspan=3, padx=4, pady=4, sticky="ew")

		rank_actions_frame = ttk.LabelFrame(top_row_frame, text="Rank Controls", padding=12)
		rank_actions_frame.pack(side="left", fill="both", expand=True)

		ttk.Label(rank_actions_frame, text="Rank Category").grid(row=0, column=0, sticky="w")
		self.rank_category_combobox = ttk.Combobox(
			rank_actions_frame,
			textvariable=self.rank_category_variable,
			values=[],
			state="readonly",
			width=18,
		)
		self.rank_category_combobox.grid(row=1, column=0, padx=(0, 6), pady=(3, 8), sticky="w")
		self.rank_category_combobox.bind("<<ComboboxSelected>>", self.on_rank_category_changed)

		ttk.Label(rank_actions_frame, text="Set Rank").grid(row=0, column=1, sticky="w")
		self.rank_value_combobox = ttk.Combobox(
			rank_actions_frame,
			textvariable=self.rank_value_variable,
			values=[],
			state="readonly",
			width=18,
		)
		self.rank_value_combobox.grid(row=1, column=1, pady=(3, 8), sticky="w")

		ttk.Button(rank_actions_frame, text="Set Rank", command=self.handle_set_rank).grid(row=2, column=0, padx=(0, 6), pady=4, sticky="ew")
		ttk.Button(rank_actions_frame, text="Increase Rank", command=self.handle_increase_rank).grid(row=2, column=1, pady=4, sticky="ew")
		ttk.Button(rank_actions_frame, text="Decrease Rank", command=self.handle_decrease_rank).grid(row=3, column=0, columnspan=2, pady=4, sticky="ew")

		session_editor_frame = ttk.LabelFrame(parent_frame, text="Set Current Session Wins/Losses/Draws", padding=12)
		session_editor_frame.pack(fill="x", pady=(10, 10))

		ttk.Label(session_editor_frame, text="Wins").grid(row=0, column=0, sticky="w")
		ttk.Entry(session_editor_frame, textvariable=self.session_wins_variable, width=8).grid(row=1, column=0, padx=(0, 10), sticky="w")

		ttk.Label(session_editor_frame, text="Losses").grid(row=0, column=1, sticky="w")
		ttk.Entry(session_editor_frame, textvariable=self.session_losses_variable, width=8).grid(row=1, column=1, padx=(0, 10), sticky="w")

		ttk.Label(session_editor_frame, text="Draws").grid(row=0, column=2, sticky="w")
		ttk.Entry(session_editor_frame, textvariable=self.session_draws_variable, width=8).grid(row=1, column=2, padx=(0, 10), sticky="w")

		ttk.Button(session_editor_frame, text="Apply Session Values", command=self.handle_apply_session_values).grid(row=1, column=3, padx=(8, 0), sticky="w")

		bottom_row_frame = ttk.Frame(parent_frame)
		bottom_row_frame.pack(fill="both", expand=True)

		self.summary_frame = ttk.LabelFrame(bottom_row_frame, text="Current Game Summary", padding=12)
		self.summary_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

		self.current_session_summary_label = ttk.Label(self.summary_frame, text="Session: W 0 | L 0 | D 0 | R 0.00")
		self.current_session_summary_label.pack(anchor="w")

		self.total_summary_label = ttk.Label(self.summary_frame, text="Total: W 0 | L 0 | D 0 | R 0.00")
		self.total_summary_label.pack(anchor="w", pady=(4, 0))

		self.rank_summary_label = ttk.Label(self.summary_frame, text="Rank: Unranked")
		self.rank_summary_label.pack(anchor="w", pady=(4, 0))

		total_actions_frame = ttk.LabelFrame(bottom_row_frame, text="Total Reset", padding=12)
		total_actions_frame.pack(side="left", fill="both")

		ttk.Button(total_actions_frame, text="Reset Total Stats for Current Game", command=self.handle_reset_total_stats).pack(fill="x")

	def on_active_game_changed(self, _event=None):
		selected_game_name = self.active_game_variable.get()
		main.set_active_game(selected_game_name)
		self.refresh_all_display_values()

	def on_stats_opacity_slider_changed(self, slider_value):
		opacity_value = int(float(slider_value))
		self.stats_overlay_opacity_variable.set(opacity_value)
		self.stats_opacity_label.config(text=f"Stats Opacity: {opacity_value}%")
		main.set_stats_overlay_opacity(opacity_value)

	def on_rank_opacity_slider_changed(self, slider_value):
		opacity_value = int(float(slider_value))
		self.rank_overlay_opacity_variable.set(opacity_value)
		self.rank_opacity_label.config(text=f"Rank Opacity: {opacity_value}%")
		main.set_rank_overlay_opacity(opacity_value)

	def on_rank_category_changed(self, _event=None):
		self.refresh_rank_summary_text()

	def save_hotkeys(self):
		main.settings.setdefault("Hotkeys", {})
		for hotkey_field_name, hotkey_value_variable in self.hotkey_variables.items():
			normalized_hotkey_text = self.normalize_hotkey_text(hotkey_value_variable.get().strip())
			hotkey_value_variable.set(normalized_hotkey_text)
			main.settings["Hotkeys"][hotkey_field_name] = normalized_hotkey_text
		main.save_settings(main.settings)
		self.register_hotkeys_for_runtime(show_message=False)
		messagebox.showinfo("Hotkeys Saved", "Hotkeys have been saved to settings.json")

	def register_hotkeys_for_runtime(self, show_message=False):
		hotkey_registration_result = main.register_hotkeys(on_hotkey_action_callback=self.on_hotkey_action_received)
		self.hotkey_status_variable.set(hotkey_registration_result.get("message", "Hotkey status unknown."))
		if show_message:
			messagebox.showinfo("Hotkey Registration", hotkey_registration_result.get("message", "Hotkey registration complete."))

	def normalize_modifier_key(self, key_symbol):
		key_symbol_lower = str(key_symbol or "").lower()
		modifier_aliases = {
			"control_l": "ctrl",
			"control_r": "ctrl",
			"control": "ctrl",
			"ctrl_l": "ctrl",
			"ctrl_r": "ctrl",
			"ctrl": "ctrl",
			"alt_l": "alt",
			"alt_r": "alt",
			"alt": "alt",
			"option_l": "alt",
			"option_r": "alt",
			"option": "alt",
			"shift_l": "shift",
			"shift_r": "shift",
			"shift": "shift",
		}
		return modifier_aliases.get(key_symbol_lower)

	def normalize_regular_key_token(self, key_token):
		key_token_lower = str(key_token or "").strip().lower().replace(" ", "")
		token_aliases = {
			"return": "enter",
			"esc": "esc",
			"escape": "esc",
			"prior": "pageup",
			"next": "pagedown",
			"pgup": "pageup",
			"pgdn": "pagedown",
			"back": "backspace",
		}
		return token_aliases.get(key_token_lower, key_token_lower)

	def format_hotkey_part_for_display(self, key_part):
		key_part_lower = str(key_part or "").lower()
		display_aliases = {
			"ctrl": "Ctrl",
			"alt": "Alt",
			"shift": "Shift",
			"enter": "Enter",
			"space": "Space",
			"tab": "Tab",
			"backspace": "Backspace",
			"delete": "Delete",
			"insert": "Insert",
			"esc": "Esc",
			"up": "Up",
			"down": "Down",
			"left": "Left",
			"right": "Right",
			"home": "Home",
			"end": "End",
			"pageup": "PageUp",
			"pagedown": "PageDown",
		}
		if key_part_lower in display_aliases:
			return display_aliases[key_part_lower]
		if key_part_lower.startswith("f") and key_part_lower[1:].isdigit():
			return key_part_lower.upper()
		if len(key_part_lower) == 1:
			return key_part_lower.upper()
		return key_part_lower.title()

	def normalize_regular_key(self, event):
		key_symbol = str(getattr(event, "keysym", "") or "")
		character = str(getattr(event, "char", "") or "")

		if not key_symbol:
			return ""

		if self.normalize_modifier_key(key_symbol):
			return ""

		special_key_mappings = {
			"Return": "enter",
			"space": "space",
			"Tab": "tab",
			"BackSpace": "backspace",
			"Delete": "delete",
			"Insert": "insert",
			"Escape": "esc",
			"Up": "up",
			"Down": "down",
			"Left": "left",
			"Right": "right",
			"Home": "home",
			"End": "end",
			"Prior": "pageup",
			"Next": "pagedown",
		}
		if key_symbol in special_key_mappings:
			return self.normalize_regular_key_token(special_key_mappings[key_symbol])

		if key_symbol.upper().startswith("F") and key_symbol[1:].isdigit():
			return self.normalize_regular_key_token(key_symbol)

		if len(character) == 1 and character.isprintable():
			return self.normalize_regular_key_token(character)

		return self.normalize_regular_key_token(key_symbol)

	def build_normalized_hotkey(self, modifiers, regular_key):
		ordered_modifier_names = ["ctrl", "alt", "shift"]
		hotkey_parts = [modifier_name for modifier_name in ordered_modifier_names if modifier_name in modifiers]
		if regular_key:
			hotkey_parts.append(self.normalize_regular_key_token(regular_key))
		display_hotkey_parts = [self.format_hotkey_part_for_display(hotkey_part) for hotkey_part in hotkey_parts]
		return "+".join(display_hotkey_parts)

	def normalize_hotkey_text(self, hotkey_text):
		hotkey_text_value = str(hotkey_text or "").strip()
		if not hotkey_text_value:
			return ""

		hotkey_text_parts = [part.strip() for part in hotkey_text_value.split("+") if part.strip()]
		normalized_modifiers = set()
		normalized_regular_key = ""

		for hotkey_text_part in hotkey_text_parts:
			normalized_modifier = self.normalize_modifier_key(hotkey_text_part)
			if normalized_modifier:
				normalized_modifiers.add(normalized_modifier)
				continue

			if not normalized_regular_key:
				normalized_regular_key = self.normalize_regular_key_token(hotkey_text_part)

		return self.build_normalized_hotkey(normalized_modifiers, normalized_regular_key)

	def set_hotkey_record_buttons_enabled(self, enabled):
		new_state = "normal" if enabled else "disabled"
		for record_button in self.hotkey_record_buttons.values():
			record_button.configure(state=new_state)

	def update_recording_preview(self):
		if not self.recording_hotkey_name or self.recording_hotkey_name not in self.hotkey_variables:
			return
		preview_hotkey_text = self.build_normalized_hotkey(self.current_recording_modifiers, "")
		self.hotkey_variables[self.recording_hotkey_name].set(preview_hotkey_text)

	def start_hotkey_recording(self, hotkey_field_name):
		if self.is_recording_hotkey:
			return

		self.is_recording_hotkey = True
		self.recording_hotkey_name = hotkey_field_name
		self.recording_original_hotkey_text = self.hotkey_variables.get(hotkey_field_name, tkinter.StringVar(value="")).get()
		self.current_recording_modifiers = set()
		main.unregister_hotkeys()
		self.hotkey_status_variable.set(f"Recording hotkey for '{hotkey_field_name}'... Press Esc to cancel.")
		self.set_hotkey_record_buttons_enabled(False)
		self.hotkey_record_buttons[hotkey_field_name].configure(text="Recording...")
		self.hotkey_variables[hotkey_field_name].set("")
		self.root_window.bind("<KeyPress>", self.on_recording_key_press)
		self.root_window.bind("<KeyRelease>", self.on_recording_key_release)
		self.root_window.focus_force()

	def on_recording_key_press(self, event):
		if not self.is_recording_hotkey:
			return "break"

		if str(event.keysym) == "Escape":
			self.cancel_hotkey_recording()
			return "break"

		normalized_modifier = self.normalize_modifier_key(event.keysym)
		if normalized_modifier:
			self.current_recording_modifiers.add(normalized_modifier)
			self.update_recording_preview()
			return "break"

		normalized_regular_key = self.normalize_regular_key(event)
		if not normalized_regular_key:
			return "break"

		normalized_hotkey = self.build_normalized_hotkey(self.current_recording_modifiers, normalized_regular_key)
		if normalized_hotkey and self.recording_hotkey_name in self.hotkey_variables:
			self.hotkey_variables[self.recording_hotkey_name].set(normalized_hotkey)

		self.finish_hotkey_recording()
		return "break"

	def on_recording_key_release(self, event):
		if not self.is_recording_hotkey:
			return "break"

		normalized_modifier = self.normalize_modifier_key(event.keysym)
		if normalized_modifier and normalized_modifier in self.current_recording_modifiers:
			self.current_recording_modifiers.discard(normalized_modifier)
			self.update_recording_preview()
		return "break"

	def finish_hotkey_recording(self):
		self.is_recording_hotkey = False
		if self.recording_hotkey_name in self.hotkey_record_buttons:
			self.hotkey_record_buttons[self.recording_hotkey_name].configure(text="Record")
		self.recording_hotkey_name = ""
		self.recording_original_hotkey_text = ""
		self.current_recording_modifiers = set()
		self.root_window.unbind("<KeyPress>")
		self.root_window.unbind("<KeyRelease>")
		self.set_hotkey_record_buttons_enabled(True)
		self.register_hotkeys_for_runtime(show_message=False)

	def cancel_hotkey_recording(self):
		if self.recording_hotkey_name in self.hotkey_variables:
			self.hotkey_variables[self.recording_hotkey_name].set(self.recording_original_hotkey_text)
		self.finish_hotkey_recording()

	def on_hotkey_action_received(self, _hotkey_action_name):
		self.root_window.after(0, self.refresh_all_display_values)

	def copy_text_to_clipboard(self, value_to_copy):
		self.root_window.clipboard_clear()
		self.root_window.clipboard_append(value_to_copy)
		self.root_window.update_idletasks()

	def copy_stats_source_url(self):
		if not self.stats_source_url:
			return
		self.copy_text_to_clipboard(self.stats_source_url)

	def copy_rank_source_url(self):
		if not self.rank_source_url:
			return
		self.copy_text_to_clipboard(self.rank_source_url)

	def copy_both_source_urls(self):
		if not self.stats_source_url or not self.rank_source_url:
			return
		combined_source_urls = f"Stats Source: {self.stats_source_url}\nRank Source: {self.rank_source_url}"
		self.copy_text_to_clipboard(combined_source_urls)

	def handle_record_win(self):
		main.record_victory()
		self.refresh_all_display_values()

	def handle_record_loss(self):
		main.record_defeat()
		self.refresh_all_display_values()

	def handle_record_draw(self):
		main.record_draw()
		self.refresh_all_display_values()

	def handle_reset_current_stats(self):
		main.reset_current_stats()
		self.refresh_all_display_values()

	def handle_set_rank(self):
		selected_rank = self.rank_value_variable.get()
		selected_rank_category = self.get_selected_rank_category_for_game()
		main.set_rank(selected_rank, rank_category=selected_rank_category)
		self.refresh_all_display_values()

	def handle_increase_rank(self):
		selected_rank_category = self.get_selected_rank_category_for_game()
		main.increase_rank(rank_category=selected_rank_category)
		self.refresh_all_display_values()

	def handle_decrease_rank(self):
		selected_rank_category = self.get_selected_rank_category_for_game()
		main.decrease_rank(rank_category=selected_rank_category)
		self.refresh_all_display_values()

	def handle_apply_session_values(self):
		try:
			wins_value = int(self.session_wins_variable.get())
			losses_value = int(self.session_losses_variable.get())
			draws_value = int(self.session_draws_variable.get())
		except ValueError:
			messagebox.showerror("Invalid Input", "Wins, losses, and draws must all be whole numbers.")
			return

		main.set_current_session_stats(wins=wins_value, losses=losses_value, draws=draws_value)
		self.refresh_all_display_values()

	def handle_reset_total_stats(self):
		confirmation = messagebox.askyesno(
			"Confirm Total Reset",
			"Reset all total stats and rank data for the active game?",
		)
		if not confirmation:
			return
		main.reset_total_stats()
		self.refresh_all_display_values()

	def get_selected_rank_category_for_game(self):
		category_names = main.get_rank_categories_for_game(main.current_game)
		if not category_names:
			return None
		selected_rank_category = self.rank_category_variable.get()
		if selected_rank_category not in category_names:
			return category_names[0]
		return selected_rank_category

	def refresh_rank_controls(self):
		active_game_name = main.current_game
		rank_categories = main.get_rank_categories_for_game(active_game_name)

		if rank_categories:
			self.rank_category_combobox.configure(values=rank_categories, state="readonly")
			if self.rank_category_variable.get() not in rank_categories:
				self.rank_category_variable.set(rank_categories[0])
		else:
			self.rank_category_combobox.configure(values=["Single Rank"], state="disabled")
			self.rank_category_variable.set("Single Rank")

		available_ranks = ["Unranked"] + list(main.game_rank_lists.get(active_game_name, []))
		self.rank_value_combobox.configure(values=available_ranks)

		selected_rank_category = self.get_selected_rank_category_for_game()
		current_rank = main.get_rank_for_category(active_game_name, selected_rank_category)
		if current_rank not in available_ranks:
			current_rank = "Unranked"
		self.rank_value_variable.set(current_rank)

	def refresh_session_editor_values(self):
		current_session_data = main.get_active_game_current_session_data()
		self.session_wins_variable.set(str(current_session_data.get("Wins", 0)))
		self.session_losses_variable.set(str(current_session_data.get("Losses", 0)))
		self.session_draws_variable.set(str(current_session_data.get("Draws", 0)))

	def refresh_summary_labels(self):
		session_data = main.get_active_game_current_session_data()
		total_data = main.get_active_game_total_data()

		session_ratio = main.calculate_win_loss_ratio(
			wins=session_data.get("Wins", 0),
			losses=session_data.get("Losses", 0),
			draws=session_data.get("Draws", 0),
		)
		total_ratio = main.calculate_win_loss_ratio(
			wins=total_data.get("Wins", 0),
			losses=total_data.get("Losses", 0),
			draws=total_data.get("Draws", 0),
		)

		self.current_session_summary_label.config(
			text=(
				f"Session: W {session_data.get('Wins', 0)} | "
				f"L {session_data.get('Losses', 0)} | "
				f"D {session_data.get('Draws', 0)} | "
				f"R {session_ratio:.2f}"
			)
		)
		self.total_summary_label.config(
			text=(
				f"Total: W {total_data.get('Wins', 0)} | "
				f"L {total_data.get('Losses', 0)} | "
				f"D {total_data.get('Draws', 0)} | "
				f"R {total_ratio:.2f}"
			)
		)
		self.refresh_rank_summary_text()

	def refresh_rank_summary_text(self):
		active_game_name = main.current_game
		rank_categories = main.get_rank_categories_for_game(active_game_name)

		if rank_categories:
			rank_parts = []
			total_rank_data = main.get_active_game_total_data().get("Rank", {})
			for category_name in rank_categories:
				category_rank = total_rank_data.get(category_name, "Unranked")
				rank_parts.append(f"{category_name}: {category_rank}")
			rank_summary_text = "Rank: " + " | ".join(rank_parts)
		else:
			single_rank = main.get_rank_for_category(active_game_name)
			rank_summary_text = f"Rank: {single_rank}"

		self.rank_summary_label.config(text=rank_summary_text)

	def refresh_all_display_values(self):
		self.active_game_variable.set(main.current_game)
		self.stats_overlay_opacity_variable.set(int(main.settings.get("Stats Overlay Opacity", main.settings.get("Opacity", 100))))
		self.rank_overlay_opacity_variable.set(int(main.settings.get("Rank Overlay Opacity", main.settings.get("Opacity", 100))))
		self.stats_opacity_label.config(text=f"Stats Opacity: {self.stats_overlay_opacity_variable.get()}%")
		self.rank_opacity_label.config(text=f"Rank Opacity: {self.rank_overlay_opacity_variable.get()}%")

		self.refresh_rank_controls()
		self.refresh_session_editor_values()
		self.refresh_summary_labels()

	def handle_window_close(self):
		if self.is_recording_hotkey:
			self.cancel_hotkey_recording()
		main.unregister_hotkeys()
		self.root_window.destroy()


def run_gui(overlay_port=None):
	root_window = tkinter.Tk()
	StatsTrackerGui(root_window=root_window, overlay_port=overlay_port)
	root_window.mainloop()


if __name__ == "__main__":
	main.main()
	run_gui()