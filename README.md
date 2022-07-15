# deforestation-analysis

## Data
### Raw
Hansen data files are downloaded as needed to save memory. Hansen-Song data files require an account to access, so are not included in this public repo, but can be found [here](https://lpdaac.usgs.gov/products/vcf5kyrv001/).

### Clean
- Aggregates of variables (e.g. loss, cover) by (country X tropics X year) for Hansen & Hansen-Song datasets
- As above, but by (country X tropics X year X binned_cover) where binned_cover is tree cover binned into 0%, 1-25%, 26-50%, 51-75%, 76-100%
## Scripts
Two main scripts process Hansen datasets:
- DataClean.py (aggregates of variables)
- DataCompress.py (compression of tiles for display in maps)

Both take significant time and memory to run, so are best run on a server. Both rely on supporting files
- countryoutlines.py (GADM country outline loading & utils)
- hansenhandler.py (Hansen dataset loading & utils)
- tile.py (Coordinate-specific Hansen utils for latitude-longitude tiles of data)

## Notebooks
### Cleaning
- combine_hansen_aggreates.ipynb
    - Combines tile aggregates, includes definition of forest threshold (50% tree cover)
- combine_hansen_compressed.ipynb
    - Combines compressed tiles for use in map graph
### Graphs
- Graphs_Line.ipynb (finished apart from comments, open to edits)
- Graphs_Map.ipynb (work in progress, open to edits but may be updated with new data)

