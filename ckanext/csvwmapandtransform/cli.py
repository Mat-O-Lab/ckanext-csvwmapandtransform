import click


@click.group(short_help="csvwmapandtransform CLI.")
def csvwmapandtransform():
    """csvwmapandtransform CLI."""
    pass


@csvwmapandtransform.command()
@click.argument("name", default="csvwmapandtransform")
def command(name):
    """Docs."""
    click.echo("Hello, {name}!".format(name=name))


def get_commands():
    return [csvwmapandtransform]
