#!/bin/sh
PROG="python3 -m warsa_linkers.units"
GET_CANDIDATES="$PROG output/prisoners_plain.ttl output/unit_candidates.ttl http://candidates/unit $ARPA_URL/warsa_actor_units --prop http://ldf.fi/schema/warsa/prisoners/unit -n -c -r 3 -w 3 --log_file output/logs/units"
JOIN="$PROG join output/unit_candidates.ttl output/unit_candidates_combined.ttl http://candidates/unit $WARSA_ENDPOINT_URL/sparql -n --prop http://candidates/unit"
CAT_ARGS="output/prisoners_plain.ttl output/periods.ttl output/unit_candidates_combined.ttl"
DISAMBIGUATE="$PROG disambiguate_validate sparql/units.sparql output/unit_all.ttl output/unit_linked_validated.ttl http://ldf.fi/schema/warsa/prisoners/warsa_unit $WARSA_ENDPOINT_URL/sparql -n --prop http://candidates/unit -r 3 -w 3 --log_file output/logs/units"

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
    cat $CAT_ARGS > output/unit_all.ttl && $DISAMBIGUATE
else
    $GET_CANDIDATES && $JOIN && cat $CAT_ARGS > output/unit_all.ttl && $DISAMBIGUATE
fi
