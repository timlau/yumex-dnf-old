#!/bin/bash


PYFILES=$(find src -name "*.py")
GLADEFILES=data/ui/*.ui
OTHERFILES=misc/*.in 
POTFILES="$PYFILES $OTHERFILES $GLADEFILES"
# Generate a new yumex-dnf.pot & a LINGUAS 

function generate_pot()
{
    cd po
    >yumex-dnf.pot
    for file in $POTFILES
    do
        xgettext --from-code=UTF-8 -j ../$file -o yumex-dnf.pot
    done
    >LINGUAS
    for po in *.po
    do
        language=${po%.po}
        echo $language >>LINGUAS
    done
    cd ..
}

generate_pot