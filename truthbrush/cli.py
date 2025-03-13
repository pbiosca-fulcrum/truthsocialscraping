"""Defines the CLI for Truthbrush."""

import json
import click
from datetime import date
import datetime
from .api import Api

api = Api()


@click.group()
def cli():
    """This is an API client for Truth Social."""


@cli.command()
@click.argument("group_id")
@click.option(
    "--limit", default=20, help="Limit the number of items returned", type=int
)
def groupposts(group_id: str, limit: int):
    """Pull posts from group timeline"""

    print(json.dumps(api.group_posts(group_id, limit)))


@cli.command()
def trends():
    """Pull trendy Truths."""

    print(json.dumps(api.trending()))


@cli.command()
def tags():
    """Pull trendy tags."""

    print(json.dumps(api.tags()))


@cli.command()
def grouptags():
    """Pull group tags."""

    print(json.dumps(api.group_tags()))


@cli.command()
def grouptrends():
    """Pull group trends."""

    print(json.dumps(api.trending_groups()))


@cli.command()
def groupsuggest():
    """Pull group suggestions."""

    print(json.dumps(api.suggested_groups()))


@cli.command()
@click.argument("handle")
def user(handle: str):
    """Pull a user's metadata."""

    print(json.dumps(api.lookup(handle)))


@cli.command()
@click.argument("query")
@click.option(
    "--searchtype",
    help="Type of search query (accounts, statuses, groups, or hashtags)",
    type=click.Choice(["accounts", "statuses", "hashtags", "groups"]),
)
@click.option(
    "--limit", default=40, help="Limit the number of items returned", type=int
)
@click.option("--resolve", help="Resolve", type=bool)
def search(searchtype: str, query: str, limit: int, resolve: bool):
    """Search for users, statuses, groups, or hashtags."""

    for page in api.search(searchtype, query, limit, resolve):
        print(json.dumps(page[searchtype]))


@cli.command()
def suggestions():
    """Pull the list of suggested users."""

    print(json.dumps(api.suggested()))


@cli.command()
def ads():
    """Pull ads."""

    print(json.dumps(api.ads()))


# @cli.command()
# @click.argument("handle")
# @click.option("--maximum", help="the maximum number of followers to pull", type=int)
# @click.option(
#     "--resume",
#     help="the `max_id` cursor to resume from, if necessary (pull this from logs to resume a failed/stalled export)",
#     type=str,
# )
# def followers(handle: str, maximum: int = None, resume: str = None):
#     """Pull a user's followers."""

#     for follower in api.user_followers(handle, maximum=maximum, resume=resume):
#         print(json.dumps(follower))


# @cli.command()
# @click.argument("handle")
# @click.option(
#     "--maximum", help="the maximum number of followed users to pull", type=int
# )
# @click.option(
#     "--resume",
#     help="the `max_id` cursor to resume from, if necessary (pull this from logs to resume a failed/stalled export)",
#     type=str,
# )
# def following(handle: str, maximum: int = None, resume: str = None):
#     """Pull users a given user follows."""

#     for followed in api.user_following(handle, maximum=maximum, resume=resume):
#         print(json.dumps(followed))


@cli.command()
@click.argument("username")
@click.option(
    "--replies/--no-replies",
    default=False,
    help="Include replies when pulling posts (defaults to no replies)",
)
@click.option(
    "--created-after",
    default=None,
    help="Only pull posts created on or after the specified datetime, e.g. 2021-10-02 or 2011-11-04T00:05:23+04:00 (defaults to none). If a timezone is not specified, UTC is assumed.",
    type=datetime.datetime.fromisoformat,
)
@click.option(
    "--pinned/--all", default=False, help="Only pull pinned posts (defaults to all)"
)
def statuses(
    username: str,
    replies: bool = False,
    created_after: date = None,
    pinned: bool = False,
):
    """Pull a user's statuses"""

    # Assume UTC if no timezone is specified
    if created_after and created_after.tzinfo is None:
        created_after = created_after.replace(tzinfo=datetime.timezone.utc)

    for page in api.pull_statuses(
        username, created_after=created_after, replies=replies, pinned=pinned
    ):
        print(json.dumps(page))


@cli.command()
@click.argument("post")
@click.option("--includeall", is_flag=True, help="return all comments on post.")
@click.argument("top_num")
def likes(post: str, includeall: bool, top_num: int):
    """Pull the top_num most recent users who liked the post."""
    for page in api.user_likes(post, includeall, top_num):
        print(json.dumps(page))


@cli.command()
@click.argument("post")
@click.option(
    "--includeall", is_flag=True, help="return all comments on post. Overrides top_num."
)
@click.option(
    "--onlyfirst", is_flag=True, help="return only direct replies to specified post"
)
@click.argument("top_num")
def comments(post: str, includeall: bool, onlyfirst: bool, top_num: int = 40):
    """Pull the top_num comments on a post (defaults to all users, including replies)."""
    for page in api.pull_comments(post, includeall, onlyfirst, top_num):
        print(page)
