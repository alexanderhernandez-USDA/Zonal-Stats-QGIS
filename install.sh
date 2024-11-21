#!/bin/bash
version=`ls /usr/bin | grep -E "python3.(9|1[0-9])$" | awk '{print $1}'`
echo $version
if [[ "$version" == "" ]]; then
        echo "Need to install at least python3.9 !!"
else
	$version -m venv --without-pip zsenv
	source zsenv/bin/activate
	$version get-pip.py
    pip install -r requirements.txt
fi
