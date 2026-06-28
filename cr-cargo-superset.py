#!/usr/bin/env python3
# cr-cargo-superset.py

import glob
import os
import tomllib

def make_toml(value, depth=0):
	if type(value) is bool:
		return str(value).lower()
	elif type(value) is str:
		return f'"{value}"'
	elif type(value) is list:
		return "[" + ", ".join([make_toml(x, depth + 1) for x in value]) + "]"
	elif type(value) is dict:
		field_list = [f"{k} = {make_toml(v, depth + 1)}" for k, v in value.items()]
		if depth == 1:
			return "\n".join(field_list)
		else:
			return "[" + ", ".join(field_list) + "]"
	else:
		assert False, f"Unhandled type {type(value)}"

assert os.path.exists("gnrt_config.toml"), "Are we in third_party/rust/chromium_crates_io/ ?"

with open("Cargo.toml", "rb") as f:
	cargo_toml = tomllib.load(f)
with open("Cargo.lock", "rb") as f:
	cargo_lock = tomllib.load(f)

lock_versions = {}

for package in cargo_lock["package"]:
	name = package["name"]
	version = package["version"]
	if name in lock_versions:
		# TODO: Need to handle multiple semver-incompatible crates
		print(f"Warning: Multiple versions of crate \"{name}\" in lock file, assuming {version} > {lock_versions[name]}")
	lock_versions[name] = version

vendored_crates = set()

for crate_toml_file in glob.glob("vendor/*/Cargo.toml"):
	with open(crate_toml_file, "rb") as f:
		crate_toml = tomllib.load(f)
		name = crate_toml["package"]["name"]
		# Ignore any vendored crates not listed in the lockfile
		if name in lock_versions:
			vendored_crates.add(name)

with open("Cargo.toml.new", "w") as f:
	for section in "package", "workspace":
		print(f"[{section}]", file=f)
		if cargo_toml[section]:
			print(make_toml(cargo_toml[section], 1), file=f)
		print(file=f)

	ver_dict = {}
	dep_dict = {}

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

	for name in vendored_crates:
		if name not in ver_dict and name not in dep_dict:
			version = lock_versions[name]
			ver_dict[name] = f"={version}"

	print("[dependencies]", file=f)
	print("\n".join([f'{k} = "{v}"' for k, v in sorted(ver_dict.items())]), file=f)
	print(file=f)

	for name, fields in sorted(dep_dict.items()):
		section = f"dependencies.{name}"
		print(f"[{section}]", file=f)
		print(make_toml(fields, 1), file=f)
		print(file=f)

print("Wrote out Cargo.toml.new .")

# end cr-cargo-superset.py
