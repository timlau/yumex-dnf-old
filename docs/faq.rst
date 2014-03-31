================
FAQ
================

Misc
=============

What does the package colors mean
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* **red** is an available update
* **green** is an installed package
* **blue** is an obsoleting package (a package replacing one/more packages)
* **black** is an available package in a repository.

This is the default colors, they can be configured in the preferences.


Configuration
=============

How do it setup yumex, to not ask for password on start
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Copy the following into **/usr/share/polkit-1/rules.d/dnfdaemon-user.rules** as root

::

    polkit.addRule(function(action, subject) {
        if (action.id == "org.baseurl.DnfSystem" &&
            subject.active == true && subject.local == true &&
            subject.user == "USERNAME") {
                polkit.log(subject.user+" got access to run org.baseurl.DnfSystem");
                return polkit.Result.YES;
        }
    });

Replace **USERNAME** with your login username

.. warning:: This will also make other applications using the DnfSystem daemon run without asking for password when running as **USERNAME**
