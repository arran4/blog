To be deleted once converted into an article, notes go here.

# Test & Build & other things mixed up (need to separate)

## Go CI/CD process
```
name: Go CI/CD

on:
  push:
    # Disable branch pushes to save minutes, as per request to "maintain" structure but avoid cost
    branches-ignore:
      - '**'
    tags:
      - 'v*'
  pull_request:
    # Disable PR runs to save minutes
    branches-ignore:
      - '**'
  release:
    types: [published]
  workflow_dispatch:
    inputs:
      action:
        description: 'Action to perform'
        required: true
        default: 'lint-fix'
        type: choice
        options:
        - 'lint-fix'
        - 'build-test'
        - 'release'
      release_mode:
        description: 'Release Mode (only for release action)'
        required: false
        default: 'snapshot'
        type: choice
        options:
        - 'snapshot'
        - 'release'

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: write
  pull-requests: write

jobs:
  lint-and-fmt:
    name: Lint & Format Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v4
        with:
          go-version: 1.21.x
      - name: Run golangci-lint
        uses: golangci/golangci-lint-action@v3
        with:
          version: v1.55.2
      - name: Run go fix and go fmt
        run: |
          go fix ./...
          go fmt ./...
      - name: Check for changes
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          if ! git diff --exit-code; then
            echo "go fix or go fmt found changes."
            if [ "${{ github.event_name }}" == "workflow_dispatch" ] && [ "${{ github.event.inputs.action }}" == "lint-fix" ]; then
              # Create PR if manually triggered for lint-fix
              git config --global user.email "actions@github.com"
              git config --global user.name "GitHub Actions"
              BRANCH_NAME="fix-lint-${{ github.run_id }}"
              git checkout -b $BRANCH_NAME
              git add .
              git commit -m "fix: go fmt and go fix"
              git push origin $BRANCH_NAME
              gh pr create --title "fix: auto-linting" --body "Automated lint fixes triggered by workflow_dispatch" --base main --head $BRANCH_NAME
            else
              # Fail if not manual fix request
              exit 1
            fi
          fi

  build-and-test:
    name: Build & Test on ${{ matrix.os }}
    needs: lint-and-fmt
    if: ${{ github.event.inputs.action != 'lint-fix' }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        go-version: [1.21.x]
      fail-fast: false

    steps:
    - uses: actions/checkout@v4

    - name: Set up Go
      uses: actions/setup-go@v4
      with:
        go-version: ${{ matrix.go-version }}

    - name: Build
      run: go build -v ./...

    - name: Test
      run: go test -v ./...

    - name: Vet
      run: go vet ./...


  release:
    name: Release
    needs: [build-and-test]
    # Run on tag push (release workflow) OR manual dispatch 'release'
    if: ${{ startsWith(github.ref, 'refs/tags/v') || (github.event_name == 'workflow_dispatch' && github.event.inputs.action == 'release') }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.21'

      - name: Run GoReleaser
        uses: goreleaser/goreleaser-action@v5
        with:
          distribution: goreleaser
          version: latest
          args: >-
            release --clean
            ${{ (github.event_name == 'workflow_dispatch' && github.event.inputs.release_mode != 'release') && '--snapshot' || '' }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

```

Try keep go version latest OR simply refer to go.mod (probably preferable as defined in fewst locations)

Ensure that actions are latest.

```
- uses: actions/setup-go@v6
  with:
    # Path to go.mod, go.work, .go-version, or .tool-versions file (no go-version as we have this.)
    go-version-file: 'go.mod'
```

### Go releaser
```
project_name: $PROJECT_NAME
builds:
  -
    id: "$BINARY"
    binary: "$BINARY"
    dir: cmd/$BINARY
    env:
      - CGO_ENABLED=0
archives:
  -
    format_overrides:
      - goos: windows
        format: zip
changelog:
  sort: asc
  filters:
    exclude:
      - '^docs:'
      - '^test:'
nfpms:
  -
    vendor: $VENDOR
    homepage: $HOMEPAGE
    maintainer: $USER
    description: NA
    license: Private
    formats:
      - apk
      - deb
      - rpm
      - termux.deb
      - archlinux
    release: 1
    section: default
    priority: extra
    contents:
      - src: ./man/$PROJECT.1
        dst: /usr/share/man/man1/$PROJECT.1
        type: doc
        file_info:
          mode: 0644
dockers:
  - image_templates:
      - ghcr.io/arran4/arran4com:{{ .Tag }}
      - ghcr.io/arran4/arran4com:latest
    dockerfile: Dockerfile
    use: buildx
    goos: linux
    goarch: [amd64, arm64]
    ids: [arran4com-embedded]
brews:
  - name: cmdproxier
    tap:
      owner: arran4
      name: homebrew-tap
    commit_author:
      name: goreleaser
      email: goreleaser@localhost
scoops:
  - name: cmdproxier
    bucket:
      owner: arran4
      name: scoop-bucket

```

On simple cross platform goreleaser builds no name templates

Try keep cgo disabled where possible.

Try to output as many nfpms formats as possible. This doesn't preclude source rpm and source deb files from being generated
separately.

## Plain old C
```
name: CI/CD

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]
  release:
    types: [published]

permissions:
  contents: write
  pull-requests: write

jobs:
  build-and-test:
    name: Build & Test on ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
      fail-fast: false

    steps:
    - uses: actions/checkout@v4

    - name: Install dependencies (Linux)
      if: runner.os == 'Linux'
      run: |
        sudo apt-get update
        sudo apt-get install -y cmake build-essential

    - name: Configure CMake
      run: cmake -B build -S . -DCMAKE_BUILD_TYPE=Release

    - name: Build
      run: cmake --build build --config Release

    - name: Run Test

    - name: Upload Binaries
      if: github.event_name == 'release'
      uses: actions/upload-artifact@v4
      with:
        name: build-artifacts-${{ matrix.os }}
        path: |
          build/*.bin
          build/*.exe
          build/*.so
          build/*.dll
          build/*.dylib
          build/Release/*.bin
          build/Release/*.exe
          build/Release/*.dll

      - name: Upload Release Assets (PDF)
        if: github.event_name == 'release'
        uses: actions/upload-release-asset@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          upload_url: ${{ github.event.release.upload_url }}
          asset_path: ./doc/latex/refman.pdf
          asset_name: refman.pdf
          asset_content_type: application/pdf

      - name: Upload Release Assets (Man Pages)
        if: github.event_name == 'release'
        uses: actions/upload-release-asset@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          upload_url: ${{ github.event.release.upload_url }}
          asset_path: ./doc_man.tar.gz
          asset_name: doc_man.tar.gz
          asset_content_type: application/gzip

......

      - name: Build Debian Packages
        env:
          DEBEMAIL: "arran4@arran4.com"
          DEBFULLNAME: "Arran4"
        run: |
          VERSION=${{ steps.version.outputs.VERSION }}
          cd $PROJECT_NAME-$VERSION
          # Update changelog to match the current version
          dch --newversion "$VERSION" "Release $VERSION" --distribution unstable
          # Build source and binary packages
          debuild -sa -us -uc
          cd ..
          mkdir -p dist
          mv *.deb *.dsc *.tar.gz *.changes *.buildinfo dist/ || true

      - name: Build RPM Packages
        run: |
          VERSION=${{ steps.version.outputs.VERSION }}
          # Setup RPM build environment
          mkdir -p rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
          # We use the same tarball for RPM
          cp dist/$PROJECT_NAME-$VERSION.tar.gz rpmbuild/SOURCES/
          cp packaging/rpm/$PROJECT_NAME.spec rpmbuild/SPECS/

          # Build Source RPM - nodeps because we are on Ubuntu and don't have rpm db populated
          rpmbuild --define "_topdir $(pwd)/rpmbuild" --define "_version $VERSION" -bs rpmbuild/SPECS/$PROJECT_NAME.spec --nodeps

          # Build Binary RPM from Source RPM
          rpmbuild --define "_topdir $(pwd)/rpmbuild" --define "_version $VERSION" --rebuild rpmbuild/SRPMS/*.src.rpm --nodeps

          cp rpmbuild/SRPMS/*.src.rpm dist/
          find rpmbuild/RPMS -name "*.rpm" -exec cp {} dist/ \;

      - name: Build Docker Image
        run: |
          # Build Docker image using the context of the current directory (which includes dependencies cloned earlier)
          docker build -t $PROJECT_NAME:${{ steps.version.outputs.VERSION }} .
          # Save the image to a tarball for release
          docker save $PROJECT_NAME:${{ steps.version.outputs.VERSION }} | gzip > dist/$PROJECT_NAME-${{ steps.version.outputs.VERSION }}-docker.tar.gz

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/*
```

It's important to create, and add/commit the rpm SPEC file and debian package files. They should be in `packaging/` In-fact source files are super important for all of the projects
including ones which generate deb/rpm via other means

### Plain old C with make valgrind & tests

```
    - name: Install Valgrind
      run: sudo apt-get update && sudo apt-get install -y valgrind

    - name: Build
      run: make

    - name: Run Tests
      run: make test

    - name: Run Memory Check
      run: |
        make test
        valgrind --error-exitcode=1 --leak-check=full ./run_tests
```

## Flutter (Fastforge, moving away from)

```
env:
  FLUTTER_VERSION: '3.38.7'

jobs:

  windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
        with:
          cache: true
          flutter-version: ${{ env.FLUTTER_VERSION }}

      - name: Set up and update version
        shell: bash
        run: |
          choco install sed make yq -y
          if [[ $GITHUB_REF == refs/tags/v* ]]; then
            TAG_NAME=${GITHUB_REF#refs/tags/v}
          else
            TAG_NAME=$(yq e '.version' pubspec.yaml | cut -d '+' -f 1)
          fi
          SEMANTIC_VERSION=$TAG_NAME
          echo "SEMANTIC_VERSION=$SEMANTIC_VERSION" >> $GITHUB_ENV
          echo "FLUTTER_VERSION=${TAG_NAME}+${GITHUB_RUN_NUMBER}" >> $GITHUB_ENV
          echo "GITHUB_REPOSITORY_NAME=${GITHUB_REPOSITORY#$GITHUB_REPOSITORY_OWNER/}" >> $GITHUB_ENV
          yq -i ".version |= \"${SEMANTIC_VERSION}+\"" pubspec.yaml
          yq -i ".version += strenv(GITHUB_RUN_NUMBER)" pubspec.yaml

      - name: Release On Windows
        run: |
          flutter pub get
          flutter analyze
          flutter config --enable-windows-desktop
          dart pub global activate fastforge
          fastforge release --name onwindows
        env:
          GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}"
      - name: Compress Release
        run: Compress-Archive -Path build/windows/runner/Release/* -DestinationPath windows-release.zip
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: windows-artifact
          path: windows-release.zip
  linux:
    #runs-on: self-hosted
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
        with:
          cache: true
          flutter-version: ${{ env.FLUTTER_VERSION }}

      - name: Install Dependencies
        run: |
          sudo apt-get update -y
          sudo apt-get install -y appstream clang cmake desktop-file-utils fakeroot fuse gir1.2-appindicator3-0.1 libappindicator3-1 libappindicator3-dev libarchive-tools libgdk-pixbuf2.0-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev libgtk-3-dev libjsoncpp25 libjsoncpp-dev libmpv-dev libnotify-bin libnotify-dev libsecret-1-0 libsecret-1-dev libunwind-dev locate make mpv ninja-build patchelf pkg-config python3-pip python3-setuptools strace tar xmlstarlet zip

      - name: Install AppImage Tool
        run: |
          wget -O appimagetool "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
          chmod +x appimagetool
          mv -v appimagetool /usr/local/bin/

      - name: Set up and update version
        run: |
          curl -sS https://webi.sh/yq | sh
          if [[ $GITHUB_REF == refs/tags/v* ]]; then
            TAG_NAME=${GITHUB_REF#refs/tags/v}
          else
            TAG_NAME=$(yq e '.version' pubspec.yaml | cut -d '+' -f 1)
          fi
          SEMANTIC_VERSION=$TAG_NAME
          echo "SEMANTIC_VERSION=$SEMANTIC_VERSION" >> $GITHUB_ENV
          echo "FLUTTER_VERSION=${TAG_NAME}+${GITHUB_RUN_NUMBER}" >> $GITHUB_ENV
          echo "GITHUB_REPOSITORY_NAME=${GITHUB_REPOSITORY#$GITHUB_REPOSITORY_OWNER/}" >> $GITHUB_ENV
          yq -i ".version |= \"${SEMANTIC_VERSION}+\"" pubspec.yaml
          yq -i '.version += strenv(GITHUB_RUN_NUMBER)' pubspec.yaml

      - name: Release On Linux
        run: |
          flutter pub get
          flutter analyze
          dart pub global activate fastforge
          fastforge release --name onlinux
        env:
          GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}"
      - name: Compress Release
        run: |
          cd build/linux/x64/release/bundle
          zip -r ../../../../../linux-release.zip .
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: linux-artifact
          path: linux-release.zip

  macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
        with:
          cache: true
          flutter-version: ${{ env.FLUTTER_VERSION }}

      - name: Dependencies
        run: |
          python3 -m pip install --break-system-packages setuptools
          npm install --break-system-packages -g appdmg

      - name: Set up and update version
        run: |
          brew install yq
          if [[ $GITHUB_REF == refs/tags/v* ]]; then
            TAG_NAME=${GITHUB_REF#refs/tags/v}
          else
            TAG_NAME=$(yq e '.version' pubspec.yaml | cut -d '+' -f 1)
          fi
          SEMANTIC_VERSION=$TAG_NAME
          echo "SEMANTIC_VERSION=$SEMANTIC_VERSION" >> $GITHUB_ENV
          echo "FLUTTER_VERSION=${TAG_NAME}+${GITHUB_RUN_NUMBER}" >> $GITHUB_ENV
          echo "GITHUB_REPOSITORY_NAME=${GITHUB_REPOSITORY#$GITHUB_REPOSITORY_OWNER/}" >> $GITHUB_ENV
          yq -i ".version |= \"${SEMANTIC_VERSION}+\"" pubspec.yaml
          yq -i '.version += strenv(GITHUB_RUN_NUMBER)' pubspec.yaml

      - name: Release On Mac OS X
        run: |
          flutter pub get
          flutter analyze
          flutter config --enable-macos-desktop
          dart pub global activate fastforge
          fastforge release --name onmac
        env:
          GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}"
      - name: Compress App
        run: |
          cd build/macos/Build/Products/Release
          ditto -c -k --sequesterRsrc --keepParent "Which Browser.app" "Which Browser.app.zip"
      - name: Rename yml files
        run: |
          cd build/macos/Build/Products/Release
          mv "Which Browser.app.dSYM/Contents/Resources/Relocations/aarch64/Which Browser.yml" "Which Browser-aarch64.yml"
          mv "Which Browser.app.dSYM/Contents/Resources/Relocations/x86_64/Which Browser.yml" "Which Browser-x86_64.yml"

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: macos-artifact
          path: |
            build/macos/Build/Products/Release/Which Browser.app.zip
            build/macos/Build/Products/Release/Which Browser-aarch64.yml
            build/macos/Build/Products/Release/Which Browser-x86_64.yml

  release:
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/v')
    needs:
      - windows
      - linux
      - macos
    steps:
      - uses: actions/checkout@v4
      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts
      - name: Determine Target Tag and Upload
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          TARGET_TAG="${{ github.ref_name }}"
          echo "Current tag: $TARGET_TAG"

          # Check if this is a build tag (has +)
          if [[ "$TARGET_TAG" == *"+"* ]]; then
            BASE_TAG=$(echo "$TARGET_TAG" | cut -d'+' -f1)
            echo "Base tag potential: $BASE_TAG"

            # Check if base tag exists as a release or tag
            if gh release view "$BASE_TAG" > /dev/null 2>&1; then
              echo "Release for $BASE_TAG exists. Consolidating artifacts to $BASE_TAG."
              TARGET_TAG="$BASE_TAG"
            elif git ls-remote --tags origin "refs/tags/$BASE_TAG" | grep -q "$BASE_TAG"; then
               echo "Tag $BASE_TAG exists but no release. Consolidating artifacts to $BASE_TAG."
               TARGET_TAG="$BASE_TAG"
            else
               echo "Base tag $BASE_TAG does not exist. Staying on $TARGET_TAG."
            fi
          fi

          echo "Final Target Tag: $TARGET_TAG"
          echo "TARGET_TAG=$TARGET_TAG" >> $GITHUB_ENV

          gh release upload --clobber "$TARGET_TAG" artifacts/**/*

      - name: Publish Release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh release edit "$TARGET_TAG" --draft=false --generate-notes || gh release create "$TARGET_TAG" --draft=false --generate-notes

  update-pubspec:
    runs-on: ubuntu-latest
    needs: release
    if: startsWith(github.ref, 'refs/tags/v')
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          ref: main
          fetch-depth: 0
      - name: Update pubspec.yaml
        run: |
          TAG_NAME=${GITHUB_REF#refs/tags/v}
          VERSION=$TAG_NAME
          echo "Updating pubspec.yaml to version $VERSION"

          # Install yq
          curl -sS https://webi.sh/yq | sh
          source ~/.bashrc || true
          export PATH="$HOME/.local/bin:$PATH"

          yq -i ".version = \"$VERSION\"" pubspec.yaml

          # Check if changed
          if git diff --quiet pubspec.yaml; then
            echo "No changes to pubspec.yaml"
          else
            git config user.name "github-actions[bot]"
            git config user.email "github-actions[bot]@users.noreply.github.com"
            git add pubspec.yaml
            git commit -m "Bump version to $VERSION"
            git push origin main
          fi
```

## Documentation Github pages deploy action
```
  deploy-docs:
    name: Deploy Documentation
    needs: [build-and-test]
    # Deploy on release event or main/master push (if enabled)
    if: (github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master' || github.event_name == 'release')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

.......


      - name: Deploy to GitHub Pages
        if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master'
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./public
```

## Documentation Doxygen 2 github pages (for c stacks) - build n deploy steps

```
      - name: Install Doxygen
        run: sudo apt-get update && sudo apt-get install -y doxygen graphviz
      - name: Generate Documentation
        run: doxygen doxygen.conf

      - name: Prepare pages directory
        env:
          TAG_NAME: ${{ github.ref_name }}
        run: |
          mkdir -p gh-pages
          mkdir -p "gh-pages/$TAG_NAME"
          cp -r doxy/html/* "gh-pages/$TAG_NAME/"

          cd gh-pages
          # Remove .git if it exists from checkout so it doesn't confuse the deploy action
          rm -rf .git

          echo '<html><body><ul>' > index.html
          for d in $(ls -d */ | sed 's#/##'); do
            echo "<li><a href=\"$d/index.html\">$d</a></li>" >> index.html
          done
          echo '</ul></body></html>' >> index.html

      - name: Upload documentation
        if: github.event_name != 'pull_request' && matrix.cc == 'gcc'
        uses: actions/upload-pages-artifact@v3
        with:
          path: docs/html

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/configure-pages@v5
      - id: deploy
        uses: actions/deploy-pages@v4

```

## Documentation hugo 2 cloudflare pages

```
  deploy:
    environment:
      name: cloudflare-pages
      url: ${{ steps.cloudflare.outputs.url }}
    runs-on: ubuntu-latest
    container:
      image: hubci/hugo:0.134.0
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: true
          fetch-depth: 0

      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.22'

      - name: Update release pages and data
        env:
          GITHUB_REPOSITORY: ${{ github.repository }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: go run update_release_pages.go
        working-directory: page

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Setup Hugo
        uses: peaceiris/actions-hugo@v3
        with:
          hugo-version: '0.134.0'
          extended: true

      - name: Build site
        run: |
          hugo mod npm pack
          npm install
          hugo --minify
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        working-directory: page

      - name: Publish to Cloudflare Pages
        id: cloudflare
        uses: cloudflare/pages-action@v1
        with:
          apiToken: ${{ secrets.CF_API_TOKEN }}
          accountId: ${{ secrets.CF_ACCOUNT_ID }}
          projectName: which-browser-site
          directory: page/public

      - name: Find Cloudflare preview comment
        if: github.event_name == 'pull_request'
        uses: peter-evans/find-comment@v3
        id: fc
        with:
          issue-number: ${{ github.event.pull_request.number }}
          comment-author: 'github-actions[bot]'
          body-includes: Cloudflare Pages Preview URL

      - name: Create or update Cloudflare preview comment
        if: github.event_name == 'pull_request'
        uses: peter-evans/create-or-update-comment@v4
        with:
          comment-id: ${{ steps.fc.outputs.comment-id }}
          issue-number: ${{ github.event.pull_request.number }}
          body: |
            **Cloudflare Pages Preview URL:** ${{ steps.cloudflare.outputs.url }}
          edit-mode: replace
```


## Typescript + go, automatic releasing

```
name: Tag and Release

on:
  push:
    branches:
      - main

permissions:
  contents: write

jobs:
  tag-and-release:
    name: Tag and Release
    runs-on: ubuntu-latest
    if: "!startsWith(github.event.head_commit.message, 'chore(release):')"
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Bump version and push tag
        id: tag_version
        uses: mathieudutour/github-tag-action@v6.2
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          default_bump: patch
          create_release: false

      - name: Fetch tags and checkout
        if: steps.tag_version.outputs.new_tag
        run: |
            git fetch --tags
            git checkout ${{ steps.tag_version.outputs.new_tag }}

      - name: Set up Go
        if: steps.tag_version.outputs.new_tag
        uses: actions/setup-go@v5
        with:
          go-version: '1.23'

      - name: Set up Node.js
        if: steps.tag_version.outputs.new_tag
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        if: steps.tag_version.outputs.new_tag
        run: |
          npm ci
          sudo apt-get update
          sudo apt-get install -y gcc-mingw-w64-x86-64 gcc-aarch64-linux-gnu

      - name: Build frontend
        if: steps.tag_version.outputs.new_tag
        run: npm run build

      - name: Run GoReleaser
        if: steps.tag_version.outputs.new_tag
        uses: goreleaser/goreleaser-action@v6
        with:
          distribution: goreleaser
          version: latest
          args: release --clean
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GORELEASER_CURRENT_TAG: ${{ steps.tag_version.outputs.new_tag }}
```

When there is dart or typescript which the versions are stored in the file as in:
```package.json
  "version": "0.0.0",
```

And 

```pubspec.yaml
version: 1.0.0+1
```

We create a pathway so that by changing this file to something that's not like: `0.0.0-next` or `1.0.0+dev` it automatically
tags and runs the release process. INVERSELY if we tag without doing, it does it for us, then commits that then creates a 
new commit for the `-next` version or `+dev` version (or what ever is appropriate for that langauge) this is in addition to 
the other means of doing this. -- This does mean that the tagged might lag, but the built commit is correct.

We also need to distinguish against libraries and not, if it is a dart library and the key is populated it will also do a 
publish.


# Lint

For every langauge we run lint and format

## GO
```
  golangci:
    name: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-go@v6
        with:
          go-version-file: go.mod
      - name: golangci-lint
        uses: golangci/golangci-lint-action@v9
        with:
          version: v2.10
```

`.golangci.yml` is minimal always, constantly trying to minimize lint exceptions

## Flutter

```
      - name: Analyze
        run: flutter analyze
```

If a lint has a "fix" version, we run that too, but if it changes it has 2 options:
1. Most normal runs; run, error if diff
2. Dispatch run OR nightly/weekly/monthly; create a PR 

# Format

Format is done when ever possible, it has 2 types of modes...
1. Most normal runs; run, error if diff
2. Dispatch run OR nightly/weekly/monthly; create a PR

```
  format:
    runs-on: ubuntu-latest

    permissions:
      contents: write
      pull-requests: write

    steps:
      - uses: actions/checkout@v4

      - name: Setup Flutter
        uses: subosito/flutter-action@v2
        with:
          channel: 'stable'

      - name: Run dart format
        run: dart format .

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v6
        with:
          commit-message: "style: dart format"
          title: "style: dart format"
          body: "This PR contains changes generated by `dart format .`"
          branch: "dart-format-changes"
          base: "main"
          delete-branch: true
```

```
      - name: Format check
        run: |
          set +e
          dart format --output=show --set-exit-if-changed .
          format_exit=$?
          if [ $format_exit -ne 0 ]; then
            echo '--- git diff after format check failure ---'
            git --no-pager diff
            exit $format_exit
          fi
```

## Dart/flutter

```
  format:
    if: github.event_name == 'push' Or manual
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
      - run: dart format .
      - name: Create Pull Request
        if diff && manual dispatch otherise error if diff
        uses: peter-evans/create-pull-request@v6
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: Apply Dart format
          title: Apply Dart format
          body: Automated formatting fixes.
          branch: dart-format-${{ github.ref_name }}
          delete-branch: true
          force-push: true
```

## Formatting check and PR 

```
      - name: Analyze project source
        id: analyze
        run: dart analyze --fatal-infos > analyze_results.txt || true

      - name: Check formatting
        id: format
        run: dart format --output=none --set-exit-if-changed . > format_results.txt || true

      - name: Post comment
        if: steps.analyze.outcome == 'failure' || steps.format.outcome == 'failure'
        uses: actions/github-script@v6
        with:
          github-token: ${{secrets.GITHUB_TOKEN}}
          script: |
            const analyze_results = require('fs').readFileSync('analyze_results.txt', 'utf8');
            const format_results = require('fs').readFileSync('format_results.txt', 'utf8');
            let comment = '';
            if (steps.analyze.outcome == 'failure') {
              comment += `## 😱 Dart Analyze Failed\n\n\`\`\`\n${analyze_results}\n\`\`\`\n\n`;
            }
            if (steps.format.outcome == 'failure') {
              comment += `## 😱 Dart Format Failed\n\nThe following files are not formatted correctly:\n\n\`\`\`\n${format_results}\n\`\`\`\n\n`;
            }
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            })
```

# Deploy

## App engine

```
      - name: Deploy to App Engine
        id: deploy
        uses: google-github-actions/deploy-appengine@v2
        with:
          deliverables: app.yaml cron.yaml
          version: v1
          project_id: ${{ secrets.GCP_PROJECT }}
          credentials: ${{ secrets.GCP_CREDENTIALS }}
```

I still try build and submit to releases even if we are deploying to appengine as most apps are made in such a way it can
be run anyway.

# Release

## Fastforge Flutter (moving away from)
```
permissions:
  contents: write

jobs:
  linux:
    runs-on: ubuntu-latest
    env:
      FLUTTER_CACHE: ${{ !contains(runner.labels, 'self-hosted') }}
    steps:
      - uses: actions/checkout@v4
      - uses: dart-lang/setup-dart@v1
      - uses: subosito/flutter-action@v2
        with:
          cache: ${{ env.FLUTTER_CACHE == 'true' }}
          flutter-version: 3.27.1
      - name: Install FastForge
        run: |
          dart pub global activate fastforge_cli
      - name: Build Linux, Android and Web packages
        run: |
          fastforge release --platform linux android web --config fastforge.yaml
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  windows:
    runs-on: windows-latest
    env:
      FLUTTER_CACHE: ${{ !contains(runner.labels, 'self-hosted') }}
    steps:
      - uses: actions/checkout@v4
      - uses: dart-lang/setup-dart@v1
      - uses: subosito/flutter-action@v2
        with:
          cache: ${{ env.FLUTTER_CACHE == 'true' }}
          flutter-version: 3.27.1
      - name: Install FastForge
        run: |
          dart pub global activate fastforge_cli
      - name: Build Windows packages
        run: |
          fastforge release --platform windows --config fastforge.yaml
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  macos:
    runs-on: macos-latest
    env:
      FLUTTER_CACHE: ${{ !contains(runner.labels, 'self-hosted') }}
    steps:
      - uses: actions/checkout@v4
      - uses: dart-lang/setup-dart@v1
      - uses: subosito/flutter-action@v2
        with:
          cache: ${{ env.FLUTTER_CACHE == 'true' }}
          flutter-version: 3.27.1
      - name: Install FastForge
        run: |
          dart pub global activate fastforge_cli
      - name: Build macOS and iOS packages
        run: |
          fastforge release --platform macos ios --config fastforge.yaml
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Better:

```
env:
  FLUTTER_VERSION: '3.27.1'

jobs:
  windows:
    runs-on: windows-latest
    env:
      FLUTTER_CACHE: ${{ !contains(runner.labels, 'self-hosted') }}
    steps:
      - uses: actions/checkout@v4
      - uses: dart-lang/setup-dart@v1
      - uses: subosito/flutter-action@v2
        with:
          cache: ${{ env.FLUTTER_CACHE == 'true' }}
          flutter-version: ${{ env.FLUTTER_VERSION  }}

      - name: Set up environment vars
        shell: bash
        run: |
          TAG_NAME=$(echo ${GITHUB_REF#refs/tags/v})
          echo "SEMANTIC_VERSION=$TAG_NAME" >> $GITHUB_ENV
          echo "FLUTTER_VERSION=${TAG_NAME}+${GITHUB_RUN_NUMBER}" >> $GITHUB_ENV
          echo "GITHUB_REPOSITORY_NAME=${GITHUB_REPOSITORY#$GITHUB_REPOSITORY_OWNER/}" >> $GITHUB_ENV

      - name: Update version number
        shell: bash
        run: |
          choco install sed make yq -y
          yq -i ".version |= \"${SEMANTIC_VERSION}+\"" pubspec.yaml
          yq -i '.version += strenv(GITHUB_RUN_NUMBER)' pubspec.yaml

      - name: Release On Windows
        run: |
          flutter pub get
          flutter pub run build_runner build --delete-conflicting-outputs
          flutter config --enable-windows-desktop
          dart pub global activate flutter_distributor
          flutter_distributor release --name onwindows
        env:
          GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}"

  linux:
    runs-on: ubuntu-latest
    env:
      FLUTTER_CACHE: ${{ !contains(runner.labels, 'self-hosted') }}
    steps:
      - uses: actions/checkout@v4
      - uses: dart-lang/setup-dart@v1
      - uses: subosito/flutter-action@v2
        with:
          cache: ${{ env.FLUTTER_CACHE == 'true' }}
          flutter-version: ${{ env.FLUTTER_VERSION  }}

      - name: Install Dependencies
        run: |
          sudo apt-get update -y
          sudo apt-get install -y appstream clang cmake desktop-file-utils fakeroot fuse gir1.2-appindicator3-0.1 libappindicator3-1 libappindicator3-dev libarchive-tools libgdk-pixbuf2.0-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev libgtk-3-dev libjsoncpp25 libjsoncpp-dev libmpv-dev libnotify-bin libnotify-dev libsecret-1-0 libsecret-1-dev libunwind-dev locate make mpv ninja-build patchelf pkg-config python3-pip python3-setuptools strace tar xmlstarlet 

      - name: Install AppImage Tool
        run: |
          wget -O appimagetool "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
          chmod +x appimagetool
          mv -v appimagetool /usr/local/bin/

      - name: Set up environment vars
        run: |
          TAG_NAME=$(echo ${GITHUB_REF#refs/tags/v})
          echo "SEMANTIC_VERSION=$TAG_NAME" >> $GITHUB_ENV
          echo "FLUTTER_VERSION=${TAG_NAME}+${GITHUB_RUN_NUMBER}" >> $GITHUB_ENV
          echo "GITHUB_REPOSITORY_NAME=${GITHUB_REPOSITORY#$GITHUB_REPOSITORY_OWNER/}" >> $GITHUB_ENV

      - name: Update version number
        run: |
          curl -sS https://webi.sh/yq | sh
          yq -i ".version |= \"${SEMANTIC_VERSION}+\"" pubspec.yaml
          yq -i '.version += strenv(GITHUB_RUN_NUMBER)' pubspec.yaml

      - name: Release On Linux
        run: |
          flutter pub get
          flutter pub run build_runner build --delete-conflicting-outputs
          dart pub global activate flutter_distributor
          flutter_distributor release --name onlinux
        env:
          GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}"

  macos:
    runs-on: macos-latest
    env:
      FLUTTER_CACHE: ${{ !contains(runner.labels, 'self-hosted') }}
    steps:
      - uses: actions/checkout@v4
      - uses: dart-lang/setup-dart@v1
      - uses: subosito/flutter-action@v2
        with:
          cache: ${{ env.FLUTTER_CACHE == 'true' }}
          flutter-version: ${{ env.FLUTTER_VERSION  }}

      - name: Dependencies
        run: |
          python3 -m pip install --break-system-packages setuptools
          npm install --break-system-packages -g appdmg      

      - name: Set version environment vars
        run: |
          TAG_NAME=$(echo ${GITHUB_REF#refs/tags/v})
          echo "SEMANTIC_VERSION=$TAG_NAME" >> $GITHUB_ENV
          echo "FLUTTER_VERSION=${TAG_NAME}+${GITHUB_RUN_NUMBER}" >> $GITHUB_ENV
          echo "GITHUB_REPOSITORY_NAME=${GITHUB_REPOSITORY#$GITHUB_REPOSITORY_OWNER/}" >> $GITHUB_ENV

      - name: Update version number
        run: |
          brew install yq
          yq -i ".version |= \"${SEMANTIC_VERSION}+\"" pubspec.yaml
          yq -i '.version += strenv(GITHUB_RUN_NUMBER)' pubspec.yaml

      - name: Release On Mac OS X
        run: |
          flutter pub get
          flutter pub run build_runner build --delete-conflicting-outputs
          flutter config --enable-macos-desktop
          dart pub global activate flutter_distributor
          flutter_distributor release --name onmac
        env:
          GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}"

  release:
    runs-on: ubuntu-latest
    needs:
      - windows
      - linux
      - macos
    steps:
      - uses: actions/checkout@v4
      - name: No longer draft
        run: |
          gh release edit "$(echo ${GITHUB_REF#refs/tags/})" --draft=false
        env:
          GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}"
```

fast forge distribute options:
```

output: dist/
releases:
  - name: onlinux
    jobs:
# Broken pending: https://github.com/leanflutter/flutter_distributor/pull/221
#      - name: linux-appimage
#        package:
#          platform: linux
#          target: appimage
#        publish:
#          target: github
#          args:
#            repo-owner: arran4
#            repo-name: arrans_counter_app
      - name: linux-deb
        package:
          platform: linux
          target: deb
        publish:
          target: github
          args:
            repo-owner: arran4
            repo-name: arrans_counter_app
      - name: linux-rpm
        package:
          platform: linux
          target: rpm
        publish:
          target: github
          args:
            repo-owner: arran4
            repo-name: arrans_counter_app
      - name: linux-pacman
        package:
          platform: linux
          target: pacman
        publish:
          target: github
          args:
            repo-owner: arran4
            repo-name: arrans_counter_app
      - name: linux-zip
        package:
          platform: linux
          target: zip
        publish:
          target: github
          args:
            repo-owner: arran4
            repo-name: arrans_counter_app
      - name: android-aab
        package:
          platform: android
          target: aab
          build_args:
            target-platform: android-arm,android-arm64
        publish:
          target: github
          args:
            repo-owner: arran4
            repo-name: arrans_counter_app
      - name: android-apk
        package:
          platform: android
          target: apk
          build_args:
            target-platform: android-arm,android-arm64
        publish:
          target: github
          args:
            repo-owner: arran4
            repo-name: arrans_counter_app
      - name: web-direct
        package:
          platform: web
          target: direct
        publish:
          target: github
          args:
            repo-owner: arran4
            repo-name: arrans_counter_app
  - name: onwindows
    jobs:
      - name: windows-exe
        package:
          platform: windows
          target: exe
        publish:
          target: github
          args:
            repo-owner: arran4
            repo-name: arrans_counter_app
      - name: windows-msix
        package:
          platform: windows
          target: msix
        publish:
          target: github
          args:
            repo-owner: arran4
            repo-name: arrans_counter_app
      - name: windows-zip
        package:
          platform: windows
          target: zip
        publish:
          target: github
          args:
            repo-owner: arran4
            repo-name: arrans_counter_app
  - name: onmac
    jobs:
# Disabled for packaging reasons atm.
#      - name: ios-ipa
#        package:
#          platform: ios
#          target: ipa
#          build_args:
#            export-method: ad-hoc
#        publish:
#          target: github
#          args:
#            repo-owner: arran4
#            repo-name: arrans_counter_app
      - name: macos-dmg
        package:
          platform: macos
          target: dmg
        publish:
          target: github
          args:
            repo-owner: arran4
            repo-name: arrans_counter_app
# Disabled for packaging reasons atm.
#      - name: macos-pkg
#        package:
#          platform: macos
#          target: pkg
#        publish:
#          target: github
#          args:
#            repo-owner: arran4
#            repo-name: arrans_counter_app
      - name: macos-zip
        package:
          platform: macos
          target: zip
        publish:
          target: github
          args:
            repo-owner: arran4
            repo-name: arrans_counter_app
```

Or something like that obviously file names are more appropraite

## homebrew

```
brews:
  - name: cmdproxier
    tap:
      owner: arran4
      name: homebrew-tap
    commit_author:
      name: goreleaser
      email: goreleaser@localhost
```

# Health and saftey

Going to add gitleaks to every workflow for push and nightly/weekly/monthly runs only:
```
name: gitleaks
on:
  pull_request:
  push:
  workflow_dispatch:
  schedule:
    - cron: "0 4 * * *" # run once a day at 4 AM
jobs:
  scan:
    name: gitleaks
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

```

on: [push]

jobs:
  govulncheck_job:
    runs-on: ubuntu-latest
    name: Run govulncheck
    steps:
      - id: govulncheck
        uses: golang/govulncheck-action@v1
        with:
           go-version-input: 1.20.6
           go-package: ./...
```


# Helpers and references

## Tag change detection for dart

```
  create_tag:
    name: Create version tag
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Detect version change
        id: version
        env:
          BEFORE_SHA: ${{ github.event.before }}
        run: |
          before_ref="$BEFORE_SHA"
          if [ -z "$before_ref" ] || [ "$before_ref" = "0000000000000000000000000000000000000000" ]; then
            before_ref=$(git rev-list --max-parents=0 HEAD | tail -n 1)
          fi

          if [ -z "$before_ref" ]; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
            exit 0
          fi

          if ! git diff --name-only "$before_ref" HEAD | grep -q '^pubspec.yaml$'; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
            exit 0
          fi

          if ! git show "$before_ref":pubspec.yaml >/tmp/pubspec_before 2>/dev/null; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
            exit 0
          fi

          old_version=$(awk '/^version:/ {print $2; exit}' /tmp/pubspec_before)
          new_version=$(awk '/^version:/ {print $2; exit}' pubspec.yaml)

          if [ -z "$old_version" ] || [ -z "$new_version" ]; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
            exit 0
          fi

          if [ "$old_version" = "$new_version" ]; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
            exit 0
          fi

          tag="v${new_version%%+*}"

          echo "changed=true" >> "$GITHUB_OUTPUT"
          echo "tag=$tag" >> "$GITHUB_OUTPUT"

      - name: Create tag
        if: steps.version.outputs.changed == 'true'
        uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          script: |
            const tag = '${{ steps.version.outputs.tag }}';
            const ref = `refs/tags/${tag}`;

            try {
              await github.rest.git.getRef({
                owner: context.repo.owner,
                repo: context.repo.repo,
                ref: ref,
              });
              core.info(`Tag ${tag} already exists, skipping.`);
              return;
            } catch (error) {
              if (error.status !== 404) {
                throw error;
              }
            }

            await github.rest.git.createRef({
              owner: context.repo.owner,
              repo: context.repo.repo,
              ref: ref,
              sha: context.sha,
            });
            core.info(`Created tag ${tag} at ${context.sha}.`);
```

## Lots of ifs

```
      - name: Install dependencies
        run: dart pub get
      - name: Verify formatting
        if: ${{ matrix.os == 'ubuntu-latest' && (github.event_name == 'pull_request' || github.ref_name == 'main' || github.ref_name == 'master') }}
        run: dart format --output=none --set-exit-if-changed .
      - name: Static analysis
        run: dart analyze
      - name: Run tests
        if: ${{ matrix.os == 'ubuntu-latest' && (github.event_name == 'pull_request' || github.ref_name == 'main' || github.ref_name == 'master') }}
        run: dart test
      - name: Generate API docs
        if: ${{ matrix.os == 'ubuntu-latest' && github.event_name == 'push' && (github.ref_name == 'main' || github.ref_name == 'master') }}
        run: dart doc
```

## Partial completed dart scripted version

```
name: Dart CI and Release

on:
  push:
    branches: [ main ]
    tags:
      - 'v*'
  pull_request:
    branches: [ main ]
  workflow_dispatch:
    inputs:
      increment:
        description: 'Version increment'
        required: true
        default: 'patch'
        type: choice
        options:
          - patch
          - minor
          - major
          - manual
      manual_version:
        description: 'Manual version (if increment is manual)'
        required: false
        type: string

permissions:
  contents: write
  pull-requests: write

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dart-lang/setup-dart@v1
        with:
          sdk: stable
      - name: Install dependencies
        run: dart pub get
      - name: Verify formatting
        run: dart format --output=none --set-exit-if-changed .
        continue-on-error: true
      - name: Analyze project source
        run: dart analyze
      - name: Run tests
        run: dart test

  release:
    needs: test
    if: startsWith(github.ref, 'refs/tags/v') || github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Prepare Release (Manual Dispatch)
        if: github.event_name == 'workflow_dispatch'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          INCREMENT: ${{ inputs.increment }}
          MANUAL_VERSION_INPUT: ${{ inputs.manual_version }}
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

          # Ensure we are on main
          git checkout main
          git pull origin main

          PUBSPEC_VERSION=$(awk '/^version:/ {print $2}' pubspec.yaml)
          echo "Pubspec version: $PUBSPEC_VERSION"

          git fetch --tags
          HIGHEST_TAG=$(git tag -l "v*" | sed 's/^v//' | sort -V | tail -n 1)
          if [ -z "$HIGHEST_TAG" ]; then
             HIGHEST_TAG="0.0.0"
          fi
          echo "Highest tag: $HIGHEST_TAG"

          CURRENT_VERSION=$(echo -e "$PUBSPEC_VERSION\n$HIGHEST_TAG" | sort -V | tail -n 1)
          echo "Base version for increment: $CURRENT_VERSION"

          if [ "$INCREMENT" == "manual" ]; then
             if [ -z "$MANUAL_VERSION_INPUT" ]; then
                echo "Error: Manual version is required when increment is set to 'manual'."
                exit 1
             fi
             NEW_VERSION="$MANUAL_VERSION_INPUT"
          else
             IFS='.' read -r -a parts <<< "$CURRENT_VERSION"
             MAJOR="${parts[0]}"
             MINOR="${parts[1]}"
             PATCH="${parts[2]}"

             if [ "$INCREMENT" == "major" ]; then
               MAJOR=$((MAJOR + 1))
               MINOR=0
               PATCH=0
             elif [ "$INCREMENT" == "minor" ]; then
               MINOR=$((MINOR + 1))
               PATCH=0
             else
               PATCH=$((PATCH + 1))
             fi
             NEW_VERSION="$MAJOR.$MINOR.$PATCH"
          fi

          echo "Calculated new version: $NEW_VERSION"
          echo "NEW_VERSION=$NEW_VERSION" >> $GITHUB_ENV

          # Create release branch
          BRANCH_NAME="release/v$NEW_VERSION"
          git checkout -b "$BRANCH_NAME"

          # Update pubspec
          sed -i "s/^version: .*/version: $NEW_VERSION/" pubspec.yaml

          # Commit
          git add pubspec.yaml
          git commit -m "Bump version to $NEW_VERSION"

          # Tag
          git tag "v$NEW_VERSION"

          # Push Tag
          git push origin "v$NEW_VERSION"

          # Push Branch and Create PR
          git push origin "$BRANCH_NAME"
          gh pr create --title "Bump version to $NEW_VERSION" --body "Automated version bump to $NEW_VERSION" --base main

      - name: Verify/Update Pubspec (Tag Trigger)
        if: startsWith(github.ref, 'refs/tags/v')
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          TAG_VERSION=${GITHUB_REF#refs/tags/v}
          PUBSPEC_VERSION=$(awk '/^version:/ {print $2}' pubspec.yaml)
          if [ "$TAG_VERSION" != "$PUBSPEC_VERSION" ]; then
            echo "Version mismatch: Tag=$TAG_VERSION, Pubspec=$PUBSPEC_VERSION"
            echo "Updating pubspec.yaml on main..."

            git config user.name "github-actions[bot]"
            git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

            git fetch origin main
            git checkout main
            git pull origin main

            sed -i "s/^version: .*/version: $TAG_VERSION/" pubspec.yaml

            if git diff --quiet pubspec.yaml; then
              echo "pubspec.yaml matches tag version in main already."
            else
              git add pubspec.yaml
              git commit -m "Bump version to $TAG_VERSION"

              if git push origin main; then
                echo "Successfully pushed version update to main."
              else
                echo "Push to main failed. Creating PR."
                BRANCH_NAME="bump-version-$TAG_VERSION"
                git checkout -b "$BRANCH_NAME"
                git push origin "$BRANCH_NAME"
                gh pr create --title "Bump version to $TAG_VERSION" --body "Automated version bump matches tag $TAG_VERSION" --base main
              fi
            fi

            echo "Restoring tag checkout..."
            git checkout $GITHUB_SHA
          fi
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          generate_release_notes: true
          tag_name: ${{ env.NEW_VERSION && format('v{0}', env.NEW_VERSION) || '' }}
```

## Docker
In all cases we are using docker we need an appropraite:

```
      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}


      - name: Extract Docker metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=tag
            type=raw,value=latest,enable=${{ startsWith(github.ref, 'refs/tags/v') }}

      - name: Build and push image
        uses: docker/build-push-action@v6
        with:
          context: .
          build-contexts: dotfiles=.
          file: containers/dev-dotfiles-debian/Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

Maybe 2 Depending on which registries too


## Clean up Branch to branch PRs when a PR is closed without the prs being merged

```
name: Cleanup Auto-format PR

on:
  pull_request:
    types: [closed]

permissions:
  contents: write
  pull-requests: write

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - name: Cleanup Auto-format PR
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          HEAD_REF: ${{ github.event.pull_request.head.ref }}
          REPO: ${{ github.repository }}
        run: |
          BRANCH="auto-format-${HEAD_REF}"
          echo "Checking for auto-format PRs associated with branch: $BRANCH"

          # Find open PRs from this branch
          PR_NUMBER=$(gh pr list --head "$BRANCH" --json number -q '.[0].number')

          if [ -n "$PR_NUMBER" ]; then
            echo "Closing PR #$PR_NUMBER"
            gh pr close "$PR_NUMBER" --delete-branch
          else
            echo "No open PR found for branch $BRANCH"
            # Try to delete the branch directly via API in case it exists but has no PR
            echo "Attempting to delete branch $BRANCH via API..."
            gh api -X DELETE "repos/$REPO/git/refs/heads/$BRANCH" || echo "Branch $BRANCH not found or could not be deleted"
          fi
```

## Fastforge less build (but also package lite) of flutter apps

```
name: Flutter CI/CD

on:
  push:
    branches: [ "main" ]
    tags: [ "v*" ]
  pull_request:
    branches: [ "main" ]

permissions:
  contents: write

jobs:
  format-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Flutter
        uses: subosito/flutter-action@v2
        with:
          channel: 'stable'
      - name: Verify formatting
        run: dart format --output=none --set-exit-if-changed .
        continue-on-error: true

  test-and-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Flutter
        uses: subosito/flutter-action@v2
        with:
          channel: 'stable'

      - name: Install dependencies
        run: flutter pub get

      - name: Analyze project source
        run: flutter analyze

      - name: Run tests
        run: flutter test

  build:
    needs: [test-and-lint, format-check]
    if: startsWith(github.ref, 'refs/tags/v')
    strategy:
      matrix:
        include:
          - os: ubuntu-latest
            artifact_name: Jules_Client-x86_64.AppImage
          - os: windows-latest
            artifact_name: flutter_jules-windows.zip
          - os: macos-latest
            artifact_name: flutter_jules-macos.zip

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - name: Setup Flutter
        uses: subosito/flutter-action@v2
        with:
          channel: 'stable'

      - name: Install Linux dependencies
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev libsecret-1-dev libjsoncpp-dev libayatana-appindicator3-dev libfuse2

      - name: Install dependencies
        run: flutter pub get

      - name: Build Linux
        if: runner.os == 'Linux'
        run: |
          flutter config --enable-linux-desktop
          flutter build linux --release
          ./packaging/linux/create_appimage.sh
          mv *.AppImage ${{ matrix.artifact_name }}

      - name: Build Windows
        if: runner.os == 'Windows'
        run: |
          flutter config --enable-windows-desktop
          flutter build windows --release
          Rename-Item build\windows\x64\runner\Release flutter_jules
          Compress-Archive -Path build\windows\x64\runner\flutter_jules -DestinationPath ${{ matrix.artifact_name }}

      - name: Build macOS
        if: runner.os == 'macOS'
        run: |
          flutter config --enable-macos-desktop
          flutter build macos --release
          pushd build/macos/Build/Products/Release
          zip -r $GITHUB_WORKSPACE/${{ matrix.artifact_name }} flutter_jules.app
          popd

      - name: Upload Artifact
        uses: actions/upload-artifact@v4
        with:
          name: binary-${{ matrix.os }}
          path: ${{ matrix.artifact_name }}
          retention-days: 1

  publish:
    needs: build
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/v')
    steps:
      - uses: actions/download-artifact@v4
        with:
          pattern: binary-*
          merge-multiple: true
          path: dist

      - name: Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/*
```

Currently source rpms and source debs are pointless with flutter apps as flutter can't be run without the internet.

## Flutter coverage report

```
      - name: Run tests with coverage
        run: flutter test --coverage
      - name: Upload coverage report
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: coverage/lcov.info

```


## Go tests vet ideas

```
name: CI

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Go
        uses: actions/setup-go@v5
        with:
          go-version-file: go.mod

      - name: Verify formatting
        run: |
          unformatted=$(gofmt -l .)
          if [ -n "$unformatted" ]; then
            echo "Files need gofmt:" >&2
            echo "$unformatted" >&2
            exit 1
          fi

      - name: Static analysis (go vet)
        run: go vet ./cmd/...

      - name: Unit and integration tests
        run: go test ./...

      - name: Race tests
        run: go test -race ./...
```

```
      - name: golangci-lint
        uses: golangci/golangci-lint-action@v9
        with:
          version: latest
          install-mode: goinstall

      - name: Check for changes
        id: check_changes
        run: |
          if [[ -n $(git status --porcelain) ]]; then
            echo "Changes detected"
            git status
            echo "changes_detected=true" >> $GITHUB_OUTPUT
          else
            echo "No changes detected"
            echo "changes_detected=false" >> $GITHUB_OUTPUT
          fi

      - name: Determine PR attributes
        id: pr_attributes
        env:
          HEAD_REF: ${{ github.head_ref }}
          REF_NAME: ${{ github.ref_name }}
          EVENT_NAME: ${{ github.event_name }}
        run: |
          if [[ "$EVENT_NAME" == "pull_request" ]]; then
            echo "base=$HEAD_REF" >> $GITHUB_OUTPUT
            echo "branch=update-generated-code-$HEAD_REF" >> $GITHUB_OUTPUT
            echo "title=chore: update generated code for $HEAD_REF" >> $GITHUB_OUTPUT
          else
            echo "base=$REF_NAME" >> $GITHUB_OUTPUT
            echo "branch=update-generated-code-$REF_NAME" >> $GITHUB_OUTPUT
            echo "title=chore: update generated code for $REF_NAME" >> $GITHUB_OUTPUT
          fi

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v6
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: "chore: update generated code"
          title: ${{ steps.pr_attributes.outputs.title }}
          body: "This PR updates the generated code to match the current generator logic."
          branch: ${{ steps.pr_attributes.outputs.branch }}
          delete-branch: true
          base: ${{ steps.pr_attributes.outputs.base }}
```


## Gitleaks with manual for deep

```
name: gitleaks

on:
  push:
  pull_request:
  workflow_dispatch:
    inputs:
      full_history:
        description: 'Scan entire git history'
        required: false
        default: 'false'

jobs:
  scan:
    name: gitleaks
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Run gitleaks
        if: github.event_name != 'workflow_dispatch' || github.event.inputs.full_history != 'true'
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          args: "--no-git --redact"
      - name: Run gitleaks on full history
        if: github.event_name == 'workflow_dispatch' && github.event.inputs.full_history == 'true'
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          args: "--redact"
```

## gorelaeser docker

```
dockers:
  - image_templates:
      - "ghcr.io/arran4/goa4web:{{ .Version }}-amd64"
    use: buildx
    build_flag_templates:
      - "--provenance=false"
    dockerfile: Dockerfile.goreleaser
    goos: linux
    goarch: amd64
  - image_templates:
      - "ghcr.io/arran4/goa4web:{{ .Version }}-arm64"
    use: buildx
    build_flag_templates:
      - "--provenance=false"
    dockerfile: Dockerfile.goreleaser
    goos: linux
    goarch: arm64
docker_manifests:
  - name_template: "ghcr.io/arran4/goa4web:{{ .Version }}"
    image_templates:
      - "ghcr.io/arran4/goa4web:{{ .Version }}-amd64"
      - "ghcr.io/arran4/goa4web:{{ .Version }}-arm64"
  - name_template: "ghcr.io/arran4/goa4web:latest"
    image_templates:
      - "ghcr.io/arran4/goa4web:{{ .Version }}-amd64"
      - "ghcr.io/arran4/goa4web:{{ .Version }}-arm64"
```

## SQLC regeneration (if used)
```
      - name: Install sqlc
        run: go install github.com/sqlc-dev/sqlc/cmd/sqlc@latest
      - name: Generate code
        run: sqlc generate
      - name: Check for changes
        id: diff
        run: |
          if [[ -n $(git status --porcelain) ]]; then
            echo "changed=true" >> "$GITHUB_OUTPUT"
          fi
      - name: Create Pull Request
        if: steps.diff.outputs.changed == 'true'
        uses: peter-evans/create-pull-request@v5
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: 'chore(sqlc): regenerate code'
          branch: sqlc-autogen-${{ github.ref_name }}
          base: ${{ github.ref_name }}
          title: 'Update sqlc generated files'
          body: |
            This PR updates generated code after SQL file changes.
```

Should have a PR clean up step too

## QT C++ basis

```
name: Qt C++ CI/CD

on:
  push:
    # Disable branch pushes to save minutes
    branches-ignore:
      - '**'
    tags:
      - 'v*'
  pull_request:
    # Disable PR runs to save minutes
    branches-ignore:
      - '**'
  release:
    types: [published]
  workflow_dispatch:
    inputs:
      action:
        description: 'Action to perform'
        required: true
        default: 'lint-fix'
        type: choice
        options:
        - 'lint-fix'
        - 'build-test'
        - 'release'
      release_mode:
        description: 'Release Mode (only for release action)'
        required: false
        default: 'snapshot'
        type: choice
        options:
        - 'snapshot'
        - 'release'

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: write
  pull-requests: write

jobs:
  lint-and-fmt:
    name: Lint & Format Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install Lint Tools
        run: |
          sudo apt-get update
          sudo apt-get install -y clang-format cppcheck

      - name: Run clang-format
        run: |
          find src -name "*.cpp" -o -name "*.h" | xargs clang-format -i -style=file || true

      - name: Run cppcheck
        run: |
          cppcheck --enable=warning,style,performance,portability --suppress=missingIncludeSystem --suppress=missingInclude --suppress=unusedFunction --suppress=constVariablePointer --suppress=unknownMacro --error-exitcode=1 src/

      - name: Check for changes
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          if ! git diff --exit-code; then
            echo "clang-format found changes."
            if [ "${{ github.event_name }}" == "workflow_dispatch" ] && [ "${{ github.event.inputs.action }}" == "lint-fix" ]; then
              # Create PR if manually triggered for lint-fix
              git config --global user.email "actions@github.com"
              git config --global user.name "GitHub Actions"
              BRANCH_NAME="fix-lint-${{ github.run_id }}"
              git checkout -b $BRANCH_NAME
              git add .
              git commit -m "fix: clang-format"
              git push origin $BRANCH_NAME
              gh pr create --title "fix: auto-linting" --body "Automated lint fixes triggered by workflow_dispatch" --base main --head $BRANCH_NAME
            else
              # Fail if not manual fix request
              exit 1
            fi
          fi

  build-and-test:
    name: Build & Test on ${{ matrix.os }}
    needs: lint-and-fmt
    if: ${{ github.event.inputs.action != 'lint-fix' }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest]
      fail-fast: false

    steps:
    - uses: actions/checkout@v4

    - name: Install Dependencies (Linux)
      if: runner.os == 'Linux'
      run: |
        sudo apt-get update
        sudo apt-get install -y qtbase5-dev qttools5-dev-tools libqt5svg5-dev cmake build-essential

    - name: Configure CMake
      run: cmake -S . -B build -DCMAKE_BUILD_TYPE=Release

    - name: Build
      run: cmake --build build --config Release

    - name: Verify Binary
      run: |
        if [ -f build/Kgithub-notify ]; then
          echo "Binary built successfully"
        else
          echo "Binary not found"
          exit 1
        fi

    - name: Upload Binaries
      uses: actions/upload-artifact@v4
      with:
        name: build-artifacts-${{ matrix.os }}
        path: build/Kgithub-notify

  release:
    name: Release
    needs: [build-and-test]
    if: ${{ startsWith(github.ref, 'refs/tags/v') || (github.event_name == 'workflow_dispatch' && github.event.inputs.action == 'release') }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download Artifacts
        uses: actions/download-artifact@v4
        with:
          name: build-artifacts-ubuntu-latest
          path: build

      - name: Create Release
        uses: softprops/action-gh-release@v1
        if: startsWith(github.ref, 'refs/tags/v')
        with:
          files: build/Kgithub-notify
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Create Snapshot Release (Manual)
        if: github.event_name == 'workflow_dispatch'
        uses: softprops/action-gh-release@v1
        with:
          tag_name: snapshot-${{ github.run_id }}
          name: Snapshot ${{ github.run_id }}
          draft: false
          prerelease: ${{ github.event.inputs.release_mode == 'snapshot' }}
          files: build/Kgithub-notify
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```