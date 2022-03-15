from io import TextIOWrapper
from typing import List, Generator

import ijson
import click
import nesteddictionary

DEFAULT_FIELDS: List[str] = [
    'referenced_tweets.author.username',
    'referenced_tweets.type',
    'author_id',
    'created_at',
    'id',
    'source',
    'text'
]


def filter_tweet(tweet, fields):
    if isinstance(tweet, list):
        return [filter_tweet(t, fields) for t in tweet]

    filtered_tweet = {}
    for field in fields:
        sub_fields = field.split('.')
        first_field = sub_fields[0]
        if len(sub_fields) == 1:
            filtered_tweet[first_field] = tweet[first_field] if first_field in tweet else None
        else:
            nested_sub_fields = '.'.join(sub_fields[1:])
            if first_field in tweet:
                sub_tweet = filter_tweet(tweet[first_field], [nested_sub_fields])

                if first_field not in filtered_tweet:
                    filtered_tweet[first_field] = sub_tweet
                else:
                    if isinstance(filtered_tweet[first_field], list):
                        filtered_tweet[first_field] = [dict_a | dict_b for dict_a,dict_b
                                                       in zip(filtered_tweet[first_field], sub_tweet)]
            else:
                filtered_tweet[first_field] = None

    return filtered_tweet


def generate_nested_keys(tweet, fields):
    nested_tweet = nesteddictionary.NestedDict(tweet)
    final_fields = [f.split('.')[-1] for f in fields]
    header_keys = []
    for field in final_fields:
        found_keys = nested_tweet.findall(field)
        if len(found_keys) > 0:
            header_keys.append('.'.join([str(x) for x in found_keys[0]]))
    return header_keys


def load_json_file(infile) -> Generator:
    json_file = ijson.items(infile, '', multiple_values=True)
    generator: Generator = (o for o in json_file)
    return generator


@click.command()
@click.option('--infile', required=False, type=click.STRING)
@click.option('--outfile', required=False, type=click.File('w'))
@click.option('--fields', required=False, default=DEFAULT_FIELDS, multiple=True)
@click.option('--format', required=False, default='json', type=click.STRING)
@click.option('-h','--help', is_flag=True)
def filter(infile: str,
           outfile: TextIOWrapper,
           fields: List[str],
           format: str,
           help: bool):

    if help:
        click.echo("filter --infile <input_file> --outfile<output_file> [--fields <FIELDS_LIST>] [--format <FORMAT>]")
        return 0

    infile_file = open(infile, 'rb')
    tweet_generator: Generator = load_json_file(infile_file)
    csv_headers = set()
    for tweet in tweet_generator:
        filtered_tweet = filter_tweet(tweet, fields)
        if format == 'json':
            click.echo(filtered_tweet, file=outfile)
        elif format == 'csv':
            headers = generate_nested_keys(filtered_tweet, fields)
            csv_headers.update(headers)

    if format == 'csv':
        csv_headers_list = list(csv_headers)
        csv_headers_list.sort()
        click.echo(','.join(csv_headers_list), file=outfile)

        infile_file.seek(0, 0)
        tweet_generator: Generator = load_json_file(infile_file)
        for tweet in tweet_generator:
            filtered_tweet = filter_tweet(tweet, fields)
            nested_tweet = nesteddictionary.NestedDict(filtered_tweet)
            output_line = []
            for header in csv_headers_list:
                try:
                    value = nested_tweet.get(header)
                except:
                    value = ''
                output_line.append(value)
            click.echo(','.join(output_line), file=outfile)

if __name__ == '__main__':
    filter()