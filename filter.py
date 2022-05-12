import json
import click
import nesteddictionary

from io import TextIOWrapper
from typing import List
from twarc import ensure_flattened

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
                        filtered_tweet[first_field] = [dict_a | dict_b for dict_a, dict_b
                                                       in zip(filtered_tweet[first_field], sub_tweet)]
            else:
                filtered_tweet[first_field] = None

    return filtered_tweet


def generate_nested_keys(tweet, fields):
    nested_tweet = nesteddictionary.NestedDict(tweet)
    final_fields = [f.split('.')[-1] for f in fields]
    header_set = set()
    for field in final_fields:
        found_keys = nested_tweet.findall(field)
        if len(found_keys) > 0:
            for key in found_keys:
                header_set.add('.'.join([str(x) for x in key]))
    return list(header_set)


def is_tweet_related(tweet, relation):
    if 'referenced_tweets' in tweet and tweet['referenced_tweets'] is not None:
        return relation in [reference['type'] for reference in tweet['referenced_tweets']]
    else:
        return False


@click.command()
@click.option('-f', '--fields', required=False, default=None, multiple=False, type=click.STRING)
@click.option('-e', '--extension', required=False, default='json', type=click.STRING)
@click.option('-r', '--related', required=False, type=click.STRING)
@click.argument('infile', type=click.File('r'), default='-')
@click.argument('outfile', type=click.File('w'), default='-')
def twarc_filter(infile: TextIOWrapper,
                 outfile: TextIOWrapper,
                 related: str,
                 fields: str,
                 extension: str):

    if fields is None:
        fields = DEFAULT_FIELDS
    else:
        fields = fields.split(',')

    csv_headers = set()
    for line in infile:
        for tweet in ensure_flattened(json.loads(line)):
            filtered_tweet = filter_tweet(tweet, fields)
            if related is not None:
                is_add_tweet = is_tweet_related(tweet, related)
            else:
                is_add_tweet = True
            if is_add_tweet:
                if extension == 'json':
                    click.echo(filtered_tweet, file=outfile)
                elif extension == 'csv':
                    headers = generate_nested_keys(filtered_tweet, fields)
                    csv_headers.update(headers)

    if extension == 'csv':
        csv_headers_list = list(csv_headers)
        click.echo(','.join(csv_headers_list), file=outfile)

        infile.seek(0, 0)
        for line in infile:
            for tweet in ensure_flattened(json.loads(line)):
                filtered_tweet = filter_tweet(tweet, fields)
                if related is not None:
                    is_add_tweet = is_tweet_related(tweet, related)
                else:
                    is_add_tweet = True
                if is_add_tweet:
                    nested_tweet = nesteddictionary.NestedDict(filtered_tweet)
                    output_line = []
                    for header in csv_headers_list:
                        try:
                            value = nested_tweet.get(header)
                        except:
                            value = ''
                        output_line.append(value)
                    output_line_cleaned = []
                    for x in output_line:
                        if x is None:
                            x = 'None'
                        output_line_cleaned.append(x)
                    click.echo(','.join(output_line_cleaned), file=outfile)


if __name__ == '__main__':
    twarc_filter()
