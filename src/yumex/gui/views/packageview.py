# -*- coding: utf-8 -*-
#    Yum Exteder (yumex) - A graphic package management tool
#    Copyright (C) 2013 -2021 Tim Lauridsen < timlau<AT>fedoraproject<DOT>org >
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to
#    the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import logging

from gi.repository import GObject, Gtk
from yumex.common import timer, _, do_gtk_events

from yumex.gui.views.selectionview import SelectionView

logger = logging.getLogger("yumex.gui.views")


class PackageView(SelectionView):
    __gsignals__ = {
        "pkg-changed": (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,))
    }

    def __init__(self, qview, group_mode=False):
        self.logger = logging.getLogger("yumex.PackageView")
        SelectionView.__init__(self)
        self.set_name("YumexPackageView")
        self.group_mode = group_mode
        self._click_header_state = ""
        self.queue = qview.queue
        self.queue_view = qview
        self.store = self._setup_model()
        self.connect("cursor-changed", self.on_cursor_changed)
        self.connect("button-press-event", self.on_mouse_button)
        self.connect("key_press_event", self._on_key_press)
        self.state = "normal"
        self._last_selected = []
        self.popup = None
        if self.group_mode:
            self._click_header_active = True
        else:
            self._click_header_active = False

    def _setup_model(self):
        """
        Setup the model and view
        """
        store = Gtk.ListStore(GObject.TYPE_PYOBJECT, str)
        self.set_model(store)
        if self.group_mode:
            self.create_selection_colunm(
                "selected",
                click_handler=self.on_section_header_clicked_group,
                popup_handler=self.on_section_header_button,
                tooltip=_("Click to install all/remove all"),
            )
        else:
            self.create_selection_colunm(
                "selected",
                click_handler=self.on_section_header_clicked,
                popup_handler=self.on_section_header_button,
                tooltip=_("Click to select/deselect all"),
            )
        # Setup resent column
        cell2 = Gtk.CellRendererPixbuf()  # new
        cell2.set_property("icon-name", "list-add-symbolic")
        column2 = Gtk.TreeViewColumn("", cell2)
        column2.set_cell_data_func(cell2, self.new_pixbuf)
        column2.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column2.set_fixed_width(20)
        column2.set_sort_column_id(-1)
        self.append_column(column2)
        column2.set_clickable(True)

        self.create_text_column(_("Package"), "name", size=200)

        self.create_text_column(_("Version"), "fullver", size=120)
        self.create_text_column(_("Arch."), "arch", size=60)
        self.create_text_column(_("Size"), "sizeM", size=60)
        self.create_text_column(_("Summary"), "summary", size=600)
        self.create_text_column(_("Repository"), "repository", size=90)
        self.set_search_column(1)
        self.set_enable_search(True)
        # store.set_sort_column_id(1, Gtk.Gtk.SortType.ASCENDING)
        self.set_reorderable(False)
        self.set_fixed_height_mode(True)
        return store

    def _on_key_press(self, widget, event):
        shortcut = Gtk.accelerator_get_label(event.keyval, event.state)
        logger.debug(f"keyboard shotcut : {shortcut}")

        if shortcut in ("Ctrl+S"):
            self.on_section_header_clicked(widget)

    def on_section_header_button(self, widget, event):
        if event.button == 3:  # Right click
            print("Right Click on selection column header")

    def on_mouse_button(self, widget, event):
        """Handle mouse click in view."""
        if event.button == 3:  # Right Click
            x = int(event.x)
            y = int(event.y)
            pthinfo = self.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, _, _ = pthinfo
                self.grab_focus()
                self.set_cursor(path, col, 0)
                iterator = self.store.get_iter(path)
                pkg = self.store.get_value(iterator, 0)
                # Only open popup menu for installed packages
                if not pkg.installed or pkg.queued:
                    return
                self.popup = self._get_package_popup(pkg, path)
                self.popup.popup(None, None, None, None, event.button, event.time)
                return True
        else:
            return False

    def _get_package_popup(self, pkg, path):
        """Create a right click menu, for a given package."""
        # get available downgrades
        popup = Gtk.Menu()
        menu_item = Gtk.MenuItem(_("Reinstall Package"))
        menu_item.connect("activate", self.on_package_reinstall, pkg)
        popup.add(menu_item)
        # Show downgrade menu only if there is any avaliable downgrades
        do_pkgs = pkg.downgrades
        if do_pkgs:
            popup_sub = Gtk.Menu()
            for do_pkg in do_pkgs:
                menu_item = Gtk.MenuItem(str(do_pkg))
                menu_item.set_use_underline(False)
                menu_item.connect(
                    "button-press-event", self.on_package_downgrade, pkg, do_pkg
                )
                popup_sub.add(menu_item)
            popup_sub.show_all()
            menu_item = Gtk.MenuItem(_("Downgrade Package"))
            menu_item.set_submenu(popup_sub)
            popup.add(menu_item)
        popup.show_all()
        return popup

    def on_package_reinstall(self, widget, pkg):
        """Handler for package right click menu"""
        logger.debug(f"reinstall: {str(pkg)}")
        pkg.queued = "ri"
        pkg.selected = True
        self.queue.add(pkg, "ri")
        self.queue_view.refresh()
        self.queue_draw()

    def on_package_downgrade(self, widget, event, pkg, do_pkg):
        """Downgrade package right click menu handler"""
        if event.button == 1:  # Left Click
            logger.debug(f"downgrade to : {str(do_pkg)}")
            pkg.queued = "do"
            pkg.selected = True
            pkg.downgrade_po = do_pkg
            do_pkg.queued = "do"
            do_pkg.selected = True
            do_pkg.downgrade_po = pkg
            self.queue.add(do_pkg, "do")
            self.queue_view.refresh()
            self.queue_draw()

    def on_section_header_clicked(self, widget):
        """Selection column header clicked"""
        if self.state == "normal":  # deselect all
            self._last_selected = self.get_selected()
            self.select_all()
            self.state = "selected"
        elif self.state == "selected":  # select all
            self.state = "deselected"
            self.deselect_all()
        elif self.state == "deselected":  # select previous selected
            self.state = "normal"
            self.select_by_keys(self._last_selected)
            self._last_selected = []

    def on_section_header_clicked_group(self, widget):
        """Selection column header clicked"""
        if self.state == "normal":  # deselect all
            self._last_selected = self.get_selected()
            self.install_all()
            self.state = "install-all"
        elif self.state == "install-all":  # select all
            self.state = "remove-all"
            self.deselect_all()
            self.remove_all()
        elif self.state == "remove-all":  # select previous selected
            self.state = "normal"
            self.select_by_keys(self._last_selected)
            self._last_selected = []

    def on_cursor_changed(self, widget):
        """
        a new group is selected in group view
        """
        if widget.get_selection():
            (model, iterator) = widget.get_selection().get_selected()
            if model is not None and iterator is not None:
                pkg = model.get_value(iterator, 0)
                self.emit("pkg-changed", pkg)  # send the group-changed signal

    def set_header_click(self, state):
        self._click_header_active = state
        self._click_header_state = ""

    def select_all(self):
        """
        Select all packages in the view
        """
        for elem in self.store:
            obj = elem[0]
            if not obj.queued == obj.action:
                obj.queued = obj.action
                self.queue.add(obj)
                obj.set_select(not obj.selected)
        self.queue_view.refresh()
        self.queue_draw()

    def deselect_all(self):
        """
        Deselect all packages in the view
        """
        for elem in self.store:
            obj = elem[0]
            if obj.queued == obj.action:
                obj.queued = None
                self.queue.remove(obj)
                obj.set_select(not obj.selected)
        self.queue_view.refresh()
        self.queue_draw()

    def select_by_keys(self, keys):
        iterator = self.store.get_iter_first()
        while iterator is not None:
            obj = self.store.get_value(iterator, 0)
            if obj in keys and not obj.selected:
                obj.queued = obj.action
                self.queue.add(obj)
                obj.set_select(True)
            elif obj.selected:
                obj.queued = None
                self.queue.remove(obj)
                obj.set_select(False)
            iterator = self.store.iter_next(iterator)
        self.queue_view.refresh()
        self.queue_draw()

    def get_selected(self):
        selected = []
        for elem in self.store:
            obj = elem[0]
            if obj.selected:
                selected.append(obj)
        return selected

    def get_notselected(self):
        notselected = []
        for elem in self.store:
            obj = elem[0]
            if not obj.queued == obj.action:
                notselected.append(obj)
        return notselected

    def new_pixbuf(self, column, cell, model, iterator, data):
        """
        Cell Data function for recent Column, shows pixmap
        if recent Value is True.
        """
        pkg = model.get_value(iterator, 0)
        if pkg:
            action = pkg.queued
            if action:
                if action in ("u", "i", "o"):
                    icon = "list-add-symbolic"
                elif action == "ri":
                    icon = "gtk-refresh"
                elif action == "do":
                    icon = "gtk-go-down"
                else:
                    icon = "edit-delete"
                cell.set_property("visible", True)
                cell.set_property("icon-name", icon)
            else:
                cell.set_property("visible", pkg.recent)
                cell.set_property("icon-name", "document-new")
        else:
            cell.set_property("visible", False)

    @timer
    def populate(self, pkgs):
        self.freeze_child_notify()
        self.set_model(None)
        self.store.clear()
        self.set_model(self.store)
        if pkgs:
            i = 0
            for po in sorted(pkgs, key=lambda po: po.name):
                i += 1
                if i % 500:  # Handle Gtk event, so gui dont freeze
                    do_gtk_events()
                self.store.append([po, str(po)])
        self.thaw_child_notify()
        # reset the selection column header selection state
        self.state = "normal"
        self._last_selected = []

    def on_toggled(self, widget, path):
        """Package selection handler"""
        iterator = self.store.get_iter(path)
        obj = self.store.get_value(iterator, 0)
        self.toggle_package(obj)
        self.queue_view.refresh()

    def toggle_package(self, obj):
        """
        Toggle the package queue status
        @param obj:
        """
        if obj.action == "do" or obj.queued == "do":
            self._toggle_downgrade(obj)
        else:
            if obj.queued == obj.action:
                obj.queued = None
                self.queue.remove(obj)
                obj.selected = not obj.selected
            elif not self.queue.has_pkg_with_name_arch(obj):
                obj.queued = obj.action
                self.queue.add(obj)
                obj.selected = not obj.selected

    def _toggle_downgrade(self, obj):
        if obj.queued == "do":  # all-ready queued
            related_po = obj.downgrade_po
            if obj.installed:  # is obj the installed pkg ?
                self.queue.remove(related_po, "do")
            else:
                self.queue.remove(obj, "do")
            obj.queued = None
            obj.selected = False
            related_po.queued = None
            related_po.selected = False
            # the releated package
        else:
            pkgs = obj.downgrades  # get the installed po
            if pkgs:
                # downgrade the po
                pkg = pkgs[0]
                # Installed pkg is all-ready downgraded by another package
                if pkg.action == "do" or self.queue.has_pkg_with_name_arch(pkg):
                    return
                pkg.queued = "do"
                pkg.selected = True
                pkg.downgrade_po = obj
                obj.queued = "do"
                obj.selected = True
                obj.downgrade_po = pkg
                self.queue.add(obj, "do")
        self.queue_view.refresh()
        self.queue_draw()

    def install_all(self):
        """
        Select all packages in the view
        """
        for elem in self.store:
            obj = elem[0]
            if not obj.queued == obj.action and obj.action == "i":
                obj.queued = obj.action
                self.queue.add(obj)
                obj.set_select(not obj.selected)
        self.queue_view.refresh()
        self.queue_draw()

    def remove_all(self):
        """
        Select all packages in the view
        """
        for elem in self.store:
            obj = elem[0]
            if not obj.queued == obj.action and obj.action == "r":
                obj.queued = obj.action
                self.queue.add(obj)
                obj.set_select(not obj.selected)
        self.queue_view.refresh()
        self.queue_draw()
