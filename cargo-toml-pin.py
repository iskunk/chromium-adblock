#!/usr/bin/env python3
# cargo-toml-pin.py
#
# Read in Cargo.{toml,lock} in the specified directory, and generate a new
# Cargo.toml file that has all the directives of the original, but with
# exact-version pins for all the packages listed in the .lock file.
#
# Usage: ./cargo-toml-pin.py BASE-DIR > Cargo.toml
#

import glob
import os
import sys
import tomllib

base_dir = sys.argv[1]

def make_toml(value, depth=0):
	if type(value) is bool:
		return str(value).lower()
	elif type(value) is str:
		return f'"{value}"'
	elif type(value) is list:
		if depth <= 2:
			return "[\n" + "".join([" " + make_toml(x, depth + 1) + ",\n" for x in value]) + "]"
		else:
			return "[" + ", ".join([make_toml(x, depth + 1) for x in value]) + "]"
	elif type(value) is dict:
		field_list = [f"{k} = {make_toml(v, depth + 1)}" for k, v in value.items()]
		if depth == 1:
			return "\n".join(field_list)
		else:
			return "[" + ", ".join(field_list) + "]"
	else:
		assert False, f"Unhandled type {type(value)}"

with open(f"{base_dir}/Cargo.toml", "rb") as f:
	cargo_toml = tomllib.load(f)
with open(f"{base_dir}/Cargo.lock", "rb") as f:
	cargo_lock = tomllib.load(f)

lock_versions = {}

for package in cargo_lock["package"]:
	name = package["name"]
	version = package["version"]
	if name == cargo_toml["package"]["name"]:
		# Not a dependency
		continue
	if name in lock_versions:
		# TODO: Need to handle multiple semver-incompatible crates
		print(f"Warning: Multiple versions of crate \"{name}\" in lock file, assuming {version} > {lock_versions[name]}", file=sys.stderr)
	lock_versions[name] = version

ver_dict = {}	# One-line dependency entries
dep_dict = {}	# Multi-line entries

# Get all the dependency records from the original Cargo.toml file, and
# replace the version specifications with pinned .lock file versions
for name, record in cargo_toml["dependencies"].items():
	version = lock_versions.get(name)
	if type(record) is str:
		ver_dict[name] = f"={version}" if version else record
	else:
		assert type(record) is dict
		if not record["version"]:
			print(f'Warning: No version specified in Cargo.toml for dependency "{name}"!')
		if version:
			record["version"] = f"={version}"
		dep_dict[name] = record

# Add as a dependency any package in Cargo.lock that is not in the .toml,
# likewise version-pinned to the .lock file version
for name, version in lock_versions.items():
	if name not in ver_dict and name not in dep_dict:
		ver_dict[name] = f"={version}"

# Write out the new Cargo.toml file

print("# Temporary Cargo.toml file")
print(f"# Generated from {base_dir}/Cargo.{{toml,lock}}")

for section in "package", "workspace":
	print()
	print(f"[{section}]")
	if cargo_toml[section]:
		print(make_toml(cargo_toml[section], 1))

print()
print("[dependencies]")
print("\n".join([f'{k} = "{v}"' for k, v in sorted(ver_dict.items())]))

for name, fields in sorted(dep_dict.items()):
	print()
	print(f"[dependencies.{name}]")
	print(make_toml(fields, 1))

# end cargo-toml-pin.py
