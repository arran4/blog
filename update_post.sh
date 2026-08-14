#!/bin/bash
cat << 'INNER_EOF' | grep -v '<<<<<<< SEARCH' | grep -v '=======' | grep -v '>>>>>>> REPLACE' > /tmp/update.diff
<<<<<<< SEARCH
    golden := "testdata/example.golden"

    if *update {
        if err := os.WriteFile(golden, got, 0644); err != nil {
            t.Fatal(err)
        }
    }

    want, err := os.ReadFile(golden)
    if err != nil {
        t.Fatal(err)
    }
=======
    // Consider using go:embed for reliable test reads when possible
    // //go:embed testdata/example.golden
    // var exampleGolden []byte

    golden := "testdata/example.golden"

    if *update {
        if err := os.WriteFile(golden, got, 0644); err != nil {
            t.Fatal(err)
        }
    }

    want, err := os.ReadFile(golden)
    if err != nil {
        t.Fatal(err)
    }
>>>>>>> REPLACE
<<<<<<< SEARCH
    filename := filepath.Join("testdata", name+".golden")

    if *update {
        if err := os.WriteFile(filename, got, 0644); err != nil {
            t.Fatal(err)
        }
    }

    want, err := os.ReadFile(filename)
    if err != nil {
        t.Fatal(err)
    }
=======
    filename := filepath.Join("testdata", name+".golden")

    if *update {
        if err := os.WriteFile(filename, got, 0644); err != nil {
            t.Fatal(err)
        }
    }

    want, err := os.ReadFile(filename)
    if err != nil {
        t.Fatal(err)
    }
>>>>>>> REPLACE
<<<<<<< SEARCH
This aligns perfectly with agentic coding practices by ensuring complex inputs and expected outputs are clearly defined and easily regenerated, while the actual testing logic remains isolated through `fs.FS` interfaces rather than coupled to `os` functions.
=======
This aligns perfectly with agentic coding practices by ensuring complex inputs and expected outputs are clearly defined and easily regenerated, while the actual testing logic remains isolated through `fs.FS` interfaces rather than coupled to `os` functions.

### The Case for `go:embed`

While `os.ReadFile` works fine for simple local testing, I strongly recommend using `go:embed` to read your test fixture files during assertions whenever possible.

Embedding the test data directly into the test binary substantially reduces file path resolution failures, especially when tests are run from different working directories or within CI/CD pipelines and isolated agent environments. It guarantees that the expected data is always packaged alongside the test that requires it.

In practice, you would use `-update` and `os.WriteFile` to update the files on disk, but your test assertions would read the `want` state from the embedded filesystem block, ensuring rock-solid read reliability.
>>>>>>> REPLACE
INNER_EOF
