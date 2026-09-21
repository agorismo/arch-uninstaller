import os
import subprocess
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk


def get_desktop_apps():
  """Mapeia os programas instalados explicitamente (.desktop) para pegar os ícones reais."""
  try:
    result = subprocess.run(
        ["pacman", "-Qet"], capture_output=True, text=True, check=True
    )
    explicit_packages = set(
        line.split()[0] for line in result.stdout.strip().split("\n") if line
    )
  except Exception:
    return []

  app_list = []
  app_info_list = Gio.AppInfo.get_all()

  for app in app_info_list:
    if not app.should_show():
      continue

    name = app.get_display_name()
    icon = app.get_icon()
    executable = app.get_executable()

    if not executable:
      continue

    pkg_name = None
    try:
      cmd = ["pacman", "-Qo", executable]
      res = subprocess.run(cmd, capture_output=True, text=True)
      if res.returncode == 0:
        pkg_name = res.stdout.strip().split()[-2]
    except Exception:
      pass

    if pkg_name and pkg_name in explicit_packages:
      app_list.append({
          "name": name,
          "pkg": pkg_name,
          "icon": icon,
          "comment": app.get_description() or "Sem descrição.",
      })

  return sorted(app_list, key=lambda x: x["name"].lower())


class UninstallerWindow(Gtk.ApplicationWindow):

  def __init__(self, app):
    super().__init__(application=app, title="Desinstalador Arch Linux")
    self.set_default_size(500, 600)

    # Main Layout
    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    main_box.set_margin_top(15)
    main_box.set_margin_bottom(15)
    main_box.set_margin_start(15)
    main_box.set_margin_end(15)
    self.set_child(main_box)

    # Header Text
    header = Gtk.Label()
    header.set_markup(
        "<b><big>Aplicativos Instalados</big></b>\n<span"
        ' foreground="gray">Selecione um programa para desinstalar</span>'
    )
    header.set_xalign(0)
    main_box.append(header)

    # Scroll Box para a Lista
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_vexpand(True)
    scrolled.set_hexpand(True)
    main_box.append(scrolled)

    # ListBox
    self.listbox = Gtk.ListBox()
    self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
    scrolled.set_child(self.listbox)

    # Botão de Desinstalação
    self.btn_uninstall = Gtk.Button(label="Desinstalar Selecionado")
    self.btn_uninstall.add_css_class("destructive-action")
    self.btn_uninstall.connect("clicked", self.on_uninstall_clicked)
    main_box.append(self.btn_uninstall)

    self.load_apps()

  def load_apps(self):
    while child := self.listbox.get_first_child():
      self.listbox.remove(child)

    apps = get_desktop_apps()
    for app in apps:
      row = Gtk.ListBoxRow()
      row.pkg_name = app["pkg"]
      row.app_display_name = app["name"]

      box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
      box.set_margin_top(8)
      box.set_margin_bottom(8)
      box.set_margin_start(10)
      box.set_margin_end(10)

      # Ícone do App
      img = Gtk.Image()
      if app["icon"]:
        img.set_from_gicon(app["icon"])
      else:
        img.set_from_icon_name("application-x-executable")
      img.set_pixel_size(32)
      box.append(img)

      # Textos (Nome do App + Pacote)
      vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
      lbl_name = Gtk.Label(
          label=f"<b>{app['name']}</b>", use_markup=True, xalign=0
      )
      lbl_pkg = Gtk.Label(
          label=f'<span foreground="gray" size="small">Pacote:'
          f" {app['pkg']}</span>",
          use_markup=True,
          xalign=0,
      )

      vbox.append(lbl_name)
      vbox.append(lbl_pkg)
      box.append(vbox)

      row.set_child(box)
      self.listbox.append(row)

  def on_uninstall_clicked(self, button):
    selected_row = self.listbox.get_selected_row()
    if not selected_row:
      return

    pkg = selected_row.pkg_name
    name = selected_row.app_display_name

    # AlertDialog do GTK 4 (Interface moderna sem deprecation errors)
    alert = Gtk.AlertDialog()
    alert.set_message(f"Remover {name}?")
    alert.set_detail(
        f"Isso irá executar 'pacman -Rs' para remover o pacote '{pkg}' e suas"
        " dependências órfãs."
    )
    alert.set_buttons(["Cancelar", "Desinstalar"])
    alert.set_cancel_button(0)
    alert.set_default_button(1)

    alert.choose(self, None, self.on_confirm_uninstall, pkg)

  def on_confirm_uninstall(self, dialog, result, pkg):
    try:
      response = dialog.choose_finish(result)
      # Se a resposta for index 1 ("Desinstalar")
      if response == 1:
        cmd = ["pkexec", "pacman", "-Rs", "--noconfirm", pkg]
        subprocess.run(cmd, check=True)
        self.load_apps()
    except Exception:
      pass


class UninstallerApp(Gtk.Application):

  def __init__(self):
    super().__init__(application_id="com.arch.uninstaller")

  def do_activate(self):
    win = UninstallerWindow(self)
    win.present()


if __name__ == "__main__":
  app = UninstallerApp()
  app.run(None)