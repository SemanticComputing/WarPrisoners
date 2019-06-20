#!/usr/bin/env bash
set -eo pipefail

mkdir -p output

export WARSA_ENDPOINT_URL=${WARSA_ENDPOINT_URL:-http://localhost:3030/warsa}

echo "Converting to csv"
libreoffice --headless --convert-to csv:"Text - txt - csv (StarCalc)":44,34,76,1,1,11,true data/prisoners.xls --outdir data
libreoffice --headless --convert-to csv:"Text - txt - csv (StarCalc)":44,34,76,1,1,11,true data/camps.xlsx --outdir data
libreoffice --headless --convert-to csv:"Text - txt - csv (StarCalc)":44,34,76,1,1,11,true data/hospitals.xlsx --outdir data
libreoffice --headless --convert-to csv:"Text - txt - csv (StarCalc)":44,34,76,1,1,11,true data/sources.xlsx --outdir data

if [ "$1" ]
then
    echo "Using only topmost $1 rows"
    mv data/prisoners.csv data/prisoners_full.csv
    head -n $1 data/prisoners_full.csv > data/prisoners.csv
fi

# Remove dummy rows from beginning and end of CSVs
# TODO: Remove the end-of-file content in a less error prone way using Python (e.g. pruning the resources)
tail -n +4 data/camps.csv | head -n -4 > output/camps_cropped.csv
head -n -2 data/hospitals.csv > output/hospitals_cropped.csv
tail -n +2 data/sources.csv > output/sources_cropped.csv

echo "Converting camps and hospitals to ttl"
python src/csv_to_rdf.py CAMPS output/camps_cropped.csv --outdata=output/camps_raw.ttl --outschema=output/camp_schema.ttl
python src/csv_to_rdf.py HOSPITALS output/hospitals_cropped.csv --outdata=output/hospitals_raw.ttl

# Fix resource URIs
sed -r -i 's/\/prisoners\/r\_/\/prisoners\/camp_/g' output/camps_raw.ttl
sed -r -i 's/\/prisoners\/r\_/\/prisoners\/hospital_/g' output/hospitals_raw.ttl

# Combine camps and hospitals
cat output/camps_raw.ttl output/hospitals_raw.ttl > output/camps_combined.ttl

# TODO: Transform this all to Python mapping

## Fix property URIs
sed -r -i 's/:sijainti /:location /g' output/camps_combined.ttl

sed -r -i 's/:vankeuspaikannnumero /:camp_id /g' output/camps_combined.ttl
sed -r -i 's/:vankeuspaikka /:captivity_location /g' output/camps_combined.ttl
sed -r -i 's/:toiminta-aika /:time_of_operation /g' output/camps_combined.ttl
sed -r -i 's/:tietoa-vankeuspaikasta /:camp_information /g' output/camps_combined.ttl
sed -r -i 's/:valokuvat /:camp_photographs /g' output/camps_combined.ttl
sed -r -i 's/:koordinaatit\-kartalla /:coordinates /g' output/camps_combined.ttl

sed -r -i 's/:sairaala /:camp_id /g' output/camps_combined.ttl
sed -r -i 's/:sairaalan\-tyyppi /:hospital_type /g' output/camps_combined.ttl
sed -r -i 's/:tietoa-sairaalasta /:camp_information /g' output/camps_combined.ttl
sed -r -i 's/:kuvat /:camp_photographs /g' output/camps_combined.ttl
sed -r -i 's/:koordinaatit\-kartalla /:coordinates /g' output/camps_combined.ttl

python src/csv_to_rdf.py PRISONERS data/prisoners.csv --outdata=output/prisoners_plain.ttl --outschema=output/schema.ttl

cat input_rdf/schema_base.ttl output/schema.ttl > output/schema_full.ttl
rapper -i turtle output/schema_full.ttl -o turtle > output/prisoners_schema.ttl
rm output/schema_full.ttl


echo "Done"
