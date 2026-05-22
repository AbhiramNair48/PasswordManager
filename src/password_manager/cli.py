from __future__ import annotations

from pathlib import Path

import click

from .vault import AuthenticationError, CredentialNotFoundError, Vault

_DEFAULT_DB = Path.home() / ".password_manager" / "vault.db"


@click.group()
@click.option(
    "--db-path",
    default=str(_DEFAULT_DB),
    show_default=True,
    help="Path to the vault database file.",
    type=click.Path(),
)
@click.pass_context
def main(ctx: click.Context, db_path: str) -> None:
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = Path(db_path)


def _open_vault(ctx: click.Context) -> Vault:
    master = click.prompt("Master password", hide_input=True)
    db_path: Path = ctx.obj["db_path"]
    try:
        return Vault.open(master, db_path)
    except AuthenticationError as e:
        raise click.ClickException(str(e))
    except ValueError as e:
        raise click.ClickException(str(e))


@main.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize a new vault with a master password."""
    db_path: Path = ctx.obj["db_path"]
    master = click.prompt("Choose a master password", hide_input=True, confirmation_prompt=True)
    try:
        vault = Vault.initialize(master, db_path)
        vault.close()
        click.echo(f"Vault initialized at {db_path}")
    except ValueError as e:
        raise click.ClickException(str(e))


@main.command()
@click.argument("service")
@click.option("--username", "-u", prompt=True, help="Username for the service.")
@click.pass_context
def add(ctx: click.Context, service: str, username: str) -> None:
    """Add or update a credential for SERVICE."""
    password = click.prompt("Password to store", hide_input=True, confirmation_prompt=True)
    vault = _open_vault(ctx)
    try:
        vault.add(service, username, password)
        click.echo(f"Stored credential for '{service}'.")
    finally:
        vault.close()


@main.command()
@click.argument("service")
@click.pass_context
def get(ctx: click.Context, service: str) -> None:
    """Retrieve the credential for SERVICE."""
    vault = _open_vault(ctx)
    try:
        cred = vault.get(service)
        click.echo(f"Service:  {cred.service}")
        click.echo(f"Username: {cred.username}")
        click.echo(f"Password: {cred.password}")
    except CredentialNotFoundError as e:
        raise click.ClickException(str(e))
    finally:
        vault.close()


@main.command("list")
@click.pass_context
def list_cmd(ctx: click.Context) -> None:
    """List all stored services."""
    vault = _open_vault(ctx)
    try:
        entries = vault.list()
        if not entries:
            click.echo("No credentials stored.")
            return
        click.echo(f"{'Service':<30} {'Username':<30} {'Created'}")
        click.echo("-" * 75)
        for e in entries:
            click.echo(f"{e['service']:<30} {e['username']:<30} {e['created_at']}")
    finally:
        vault.close()


@main.command()
@click.argument("service")
@click.pass_context
def delete(ctx: click.Context, service: str) -> None:
    """Delete the credential for SERVICE."""
    vault = _open_vault(ctx)
    try:
        removed = vault.delete(service)
        if removed:
            click.echo(f"Deleted credential for '{service}'.")
        else:
            raise click.ClickException(f"No credential found for '{service}'.")
    finally:
        vault.close()


@main.command()
@click.argument("query")
@click.pass_context
def search(ctx: click.Context, query: str) -> None:
    """Search services by QUERY (case-insensitive substring match)."""
    vault = _open_vault(ctx)
    try:
        results = vault.search(query)
        if not results:
            click.echo(f"No services matching '{query}'.")
            return
        click.echo(f"{'Service':<30} {'Username'}")
        click.echo("-" * 55)
        for e in results:
            click.echo(f"{e['service']:<30} {e['username']}")
    finally:
        vault.close()
