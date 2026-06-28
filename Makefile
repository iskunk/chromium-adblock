# Makefile for chromium-adblock

CHROMIUM_SRC = /external/tmp/chromium/chromium-149.0.7827.196
RUST_SYSROOT = /usr/lib/rust-1.91

CP = cp

run_gnrt := tools/crates/run_gnrt.py \
	$(if $(RUST_SYSROOT),--rust-sysroot $(RUST_SYSROOT))

rust_dir = $(CHROMIUM_SRC)/third_party/rust

all: copy-files patch-files build-gnrt vendor tarball

copy-files:
	cd src && find . -xtype f -exec $(CP) --parents {} $(CHROMIUM_SRC) \;

patch-files:
	patch -p1 -d $(CHROMIUM_SRC) < core.patch

build-gnrt:
	pkg-config --version
	pkg-config --libs openssl
	cd $(CHROMIUM_SRC) && $(run_gnrt) help

vendor:
	test -d $(rust_dir).orig || cp -a $(rust_dir) $(rust_dir).orig
	cd $(rust_dir)/chromium_crates_io && $(CURDIR)/cr-cargo-superset.py && mv Cargo.toml.new Cargo.toml
	cd $(CHROMIUM_SRC) && $(run_gnrt) vendor
	gn --version
	cd $(CHROMIUM_SRC) && $(run_gnrt) gen
	cp -p \
		$(rust_dir).orig/chromium_crates_io/Cargo.toml \
		$(rust_dir).orig/chromium_crates_io/Cargo.lock \
		$(rust_dir)/chromium_crates_io/

tarball:
	(cd $(CHROMIUM_SRC) && for crate in \
		third_party/rust/* \
		third_party/rust/chromium_crates_io/vendor/* ; \
	 do \
		test -d $$crate || continue; \
		test ! -f $$crate/gnrt_config.toml || continue; \
		orig_crate=$$(echo "$$crate" | sed 's!/rust/!/rust.orig/!'); \
		test ! -d $$orig_crate \
		|| ! cmp -s $$crate/Cargo.toml $$orig_crate/Cargo.toml \
		|| continue; \
		echo $$crate; \
	 done \
	) > tmp.include.txt
	tar cJf chromium-adblock-rust.tar.xz -C $(CHROMIUM_SRC) --exclude=README.chromium -T tmp.include.txt
	rm tmp.include.txt

# end Makefile
