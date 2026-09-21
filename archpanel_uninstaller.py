#!/usr/bin/env python3
"""
Arch Uninstaller - A clean GTK-4 graphical uninstaller 4 Arch Linux.
License: MIT
"""

import os
import subprocess
import sys
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk


def get_explicit_packages() -> set:
  """Returns the set of explicitly installed packages via pacman."""
  try:
    res = subprocess.run(
        ["pacman", "-Qet"], capture_output=True, text=True, check=True
    )
    return set(
        line.split()[0] for line in res.stdout.strip().split("\n") if line
    )
  except Exception as e:
    print(f"Error querying pacman: {e}", file=sys.stderr)
    return set()


def get_desktop_apps() -> list:
  """Maps system .desktop entries to explicitly installed pacman packages."""
  explicit_pkgs = get_explicit_packages()
  apps = []

  for app_info in Gio.AppInfo.get_all():
    if not app_info.should_show():
      continue

    executable = app_info.get_executable()
    if not executable:
      continue

    # resolve package owning the executable
    pkg_name = None
    try:
      res = subprocess.run(
          ["pacman", "-Qo", executable], capture_output=True, text=True
      )
      if res.returncode == 0:
        pkg_name = res.stdout.strip().split()[-2]
    except Exception:
      pass

    if pkg_name and pkg_name in explicit_pkgs:
      apps.append({
          "name": app_info.get_display_name(),
          "pkg": pkg_name,
          "icon": app_info.get_icon(),
          "comment": app_info.get_description() or "",
      })

  # deduplicate based on package name
  unique_apps = {app["pkg"]: app for app in apps}.values()
  return sorted(unique_apps, key=lambda x: x["name"].lower())


class UninstallerWindow(Gtk.ApplicationWindow):

  def __init__(self, app):
    super().__init__(application=app, title="Arch Uninstaller")
    self.set_default_size(480, 560)

    self.all_apps = []

    # main layout container
    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    main_box.set_margin_top(12)
    main_box.set_margin_bottom(12)
    main_box.set_margin_start(12)
    main_box.set_margin_end(12)
    self.set_child(main_box)

    # search bar
    self.search_entry = Gtk.SearchEntry(
        placeholder_text="Search applications..."
    )
    self.search_entry.connect("search-changed", self.on_search_changed)
    main_box.append(self.search_entry)

    # scrolled view
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_vexpand(True)
    main_box.append(scrolled)

    # application list
    self.listbox = Gtk.ListBox()
    self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
    scrolled.set_child(self.listbox)

    # uninstall button
    self.btn_uninstall = Gtk.Button(label="Uninstall Selected")
    self.btn_uninstall.add_css_class("destructive-action")
    self.btn_uninstall.connect("clicked", self.on_uninstall_clicked)
    main_box.append(self.btn_uninstall)

    self.load_apps()

  def load_apps(self):
    self.all_apps = get_desktop_apps()
    self.filter_apps("")

  def filter_apps(self, query: str):
    # clear current list
    while child := self.listbox.get_first_child():
      self.listbox.remove(child)

    query = query.lower().strip()

    for app in self.all_apps:
      if query and (
          query not in app["name"].lower() and query not in app["pkg"].lower()
      ):
        continue

      row = Gtk.ListBoxRow()
      row.pkg_name = app["pkg"]
      row.app_name = app["name"]

      box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
      box.set_margin_top(8)
      box.set_margin_bottom(8)
      box.set_margin_start(8)
      box.set_margin_end(8)

      # icon
      img = Gtk.Image()
      if app["icon"]:
        img.set_from_gicon(app["icon"])
      else:
        img.set_from_icon_name("application-x-executable")
      img.set_pixel_size(32)
      box.append(img)

      # Labels (App Name / Package Name)
      vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
      lbl_name = Gtk.Label(
          label=f"<b>{app['name']}</b>", use_markup=True, xalign=0
      )
      lbl_pkg = Gtk.Label(
          label=f'<span foreground="#888888" size="small">{app["pkg"]}</span>',
          use_markup=True,
          xalign=0,
      )

      vbox.append(lbl_name)
      vbox.append(lbl_pkg)
      box.append(vbox)

      row.set_child(box)
      self.listbox.append(row)

  def on_search_changed(self, entry):
    self.filter_apps(entry.get_text())

  def on_uninstall_clicked(self, button):
    selected_row = self.listbox.get_selected_row()
    if not selected_row:
      return

    pkg = selected_row.pkg_name
    name = selected_row.app_name

    dialog = Gtk.AlertDialog()
    dialog.set_message(f"Remove {name}?")
    dialog.set_detail(
        f"The command 'pacman -Rs {pkg}' will be executed to remove the package"
        " and its unneeded dependencies."
    )
    dialog.set_buttons(["Cancel", "Uninstall"])
    dialog.set_cancel_button(0)
    dialog.set_default_button(1)

    dialog.choose(self, None, self.on_confirm_uninstall, pkg)

  def on_confirm_uninstall(self, dialog, result, pkg):
    try:
      response = dialog.choose_finish(result)
      if response == 1:
        cmd = ["pkexec", "pacman", "-Rs", "--noconfirm", pkg]

        # prevent terminal hijacking
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )

        if res.returncode == 0:
          self.load_apps()
        else:
          err_output = res.stderr.strip()
          if "Not authorized" in err_output or res.returncode == 126:
            self.show_error(
                "Authentication cancelled or no graphical Polkit agent"
                " active."
            )
          else:
            self.show_error(
                f"Failed to remove package:\n{err_output or 'Unknown error.'}"
            )

    except Exception as e:
      self.show_error(str(e))

  def show_error(self, message: str):
    err_dialog = Gtk.AlertDialog()
    err_dialog.set_message("Warning")
    err_dialog.set_detail(message)
    err_dialog.set_buttons(["OK"])
    err_dialog.choose(self, None, None, None)


class Application(Gtk.Application):

  def __init__(self):
    super().__init__(application_id="io.github.arch_uninstaller")

  def do_activate(self):
    win = UninstallerWindow(self)
    win.present()


if __name__ == "__main__":
  app = Application()
  app.run(sys.argv)