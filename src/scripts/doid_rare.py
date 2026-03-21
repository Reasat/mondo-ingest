"""Creates a ROBOT template to update Mondo terms with the DOID rare disease subset annotation."""
from argparse import ArgumentParser
from pathlib import Path
from typing import Union

import curies
import pandas as pd

from utils import remove_angle_brackets, get_converter

DOID_RARE_SUBSET = 'http://purl.obolibrary.org/obo/mondo#doid_rare'
ROBOT_TEMPLATE_HEADER = {
    'mondo_id': 'ID',
    'subset': 'A oboInOwl:inSubset',
    'doid_id': '>A oboInOwl:source',
}


def get_formatted_doid_rare_df(doid_rare_tsv_path: Union[str, Path], onto_config_path: Union[str, Path]):
    """Read & reformat DOID rare disease query results"""
    conv: curies.Converter = get_converter(onto_config_path)
    # Read
    df = pd.read_csv(doid_rare_tsv_path, sep='\t').rename(columns={
        '?cls': 'doid_id',
        '?lbl': 'doid_label',
    }).sort_values(['doid_id', 'doid_label'])
    # - strip language tags (e.g. "label"@en -> label) and deduplicate
    df['doid_label'] = df['doid_label'].map(lambda x: str(x).split('@')[0].strip('"'))
    df = df.drop_duplicates(subset=['doid_id', 'doid_label'])

    # Preprocess
    # - Strip annoying angle brackets from URIs
    df['doid_id'] = df['doid_id'].map(remove_angle_brackets)
    # - Compress class IDs
    df['doid_id'] = df['doid_id'].map(lambda x: conv.compress(x))

    # All terms get the same subset
    df['subset'] = DOID_RARE_SUBSET
    return df


def create_doid_rare_robot_template(
    doid_rare_tsv_path: Union[str, Path], mondo_mappings_path: Union[str, Path], onto_config_path: Union[str, Path],
    outpath: Union[str, Path],
) -> pd.DataFrame:
    """Creates a ROBOT template to update Mondo terms with the DOID rare disease subset annotation."""
    # Get mondo.sssom.tsv
    mondo_df = pd.read_csv(mondo_mappings_path, sep='\t', comment='#').rename(columns={
        'subject_id': 'mondo_id',
        'subject_label': 'mondo_label',
    })
    # - keep only exact matches
    mondo_df = mondo_df[mondo_df['predicate_id'] == 'skos:exactMatch']

    # Get DOID rare disease TSV
    df: pd.DataFrame = get_formatted_doid_rare_df(doid_rare_tsv_path, onto_config_path)

    # JOIN to get Mondo IDs
    df = df.merge(mondo_df, how='inner', left_on='doid_id', right_on='object_id')

    # Column order, column filtering, and sorting
    df = df[['mondo_id', 'doid_id', 'subset', 'mondo_label', 'doid_label']]\
        .sort_values(['mondo_id', 'doid_id'])

    # Save & return
    df_out = pd.concat([pd.DataFrame([ROBOT_TEMPLATE_HEADER]), df])
    df_out.to_csv(outpath, sep='\t', index=False)
    return df


def cli():
    """Command line interface."""
    parser = ArgumentParser('Creates a ROBOT template to update Mondo terms with the DOID rare disease subset annotation.')
    parser.add_argument(
        '-d', '--doid-rare-tsv-path', required=True,
        help='Path to TSV containing results of a SPARQL query to get all DOID rare disease slim members.')
    parser.add_argument(
        '-m', '--mondo-mappings-path', required=True,
        help='Path to TSV containing all known Mondo mappings, in SSSOM format.')
    parser.add_argument(
        '-c', '--onto-config-path', required=True,
        help='Path to a config `.yml` for the ontology which contains a `base_prefix_map` which contains a '
             'list of prefixes owned by the ontology. Used to filter out terms.')
    parser.add_argument('-o', '--outpath', required=True, help='Path to save ROBOT template TSV.')
    create_doid_rare_robot_template(**vars(parser.parse_args()))


if __name__ == '__main__':
    cli()
