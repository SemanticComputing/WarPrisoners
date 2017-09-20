#!/bin/bash
PROG="python3 -m warsa_linkers.units"
GET_CANDIDATES="$PROG data/new/prisoners.ttl data/new/unit_candidates.ttl http://candidates/unit http://demo.seco.tkk.fi/arpa/warsa_actor_units --prop http://ldf.fi/schema/warsa/prisoners/unit -n -c -r 3 -w 3"
JOIN="$PROG join data/new/unit_candidates.ttl data/new/unit_candidates_combined.ttl http://candidates/unit http://localhost:3030/warsa/sparql -n --prop http://candidates/unit"
CAT_ARGS="data/new/prisoners.ttl data/new/periods.ttl data/new/unit_candidates_combined.ttl"
DISAMBIGUATE="$PROG disambiguate_validate sparql/units.sparql data/new/unit_all.ttl data/new/unit_linked_validated.ttl http://ldf.fi/schema/warsa/prisoners/warsa_unit http://localhost:3030/warsa/sparql -n --prop http://candidates/unit -r 3 -w 3"

only_disambiguate=false

while getopts ":d" opt; do
    case $opt in
        d)
            only_disambiguate=true
            ;;
        \?)
            echo "-d for disambiguate only, no arguments for complete process" >&2
            exit 1
            ;;
    esac
done

if [ "$only_disambiguate" = true ]; then
    cat $CAT_ARGS > data/new/unit_all.ttl && $DISAMBIGUATE
else
    $GET_CANDIDATES && $JOIN && cat $CAT_ARGS > data/new/unit_all.ttl && $DISAMBIGUATE
fi
