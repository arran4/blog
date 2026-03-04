Code samples:

```
// FileSystem abstraction for file operations
type FileSystem interface {
	Create(name string) (io.WriteCloser, error)
}

// RealFS implementation of FileSystem using os package
type RealFS struct{}

// Create creates a file on the real filesystem
func (RealFS) Create(name string) (io.WriteCloser, error) {
	return os.Create(name)
}


type MockFS struct {
	Files map[string]*bytes.Buffer
	Err   error
}

func (m *MockFS) Create(name string) (io.WriteCloser, error) {
	if m.Err != nil {
		return nil, m.Err
	}
	if m.Files == nil {
		m.Files = make(map[string]*bytes.Buffer)
	}
	buf := new(bytes.Buffer)
	m.Files[name] = buf
	return &nopCloser{buf}, nil
}

type nopCloser struct {
	io.Writer
}

func (nopCloser) Close() error { return nil }

.....


func TestRunCompetition_Security(t *testing.T) {
	// We only test invalid paths because valid paths would trigger the full competition which is slow.

	invalidPaths := []string{
		"../report.md",
		"/tmp/report.md",
		"subdir/report.md",
	}

	for _, p := range invalidPaths {
		args := []string{"-o", p}
		err := runCompetition(args, &MockFS{})
		if err == nil {
			t.Errorf("runCompetition with path %q should have failed", p)
		} else if err.Error() != "security error: output file must be in the current directory" {
			t.Errorf("runCompetition with path %q failed with unexpected error: %v", p, err)
		}
	}
}

```

https://pkg.go.dev/golang.org/x/tools/txtar#FS

```
type Discoverer struct {
	ExecLookPath func(string) (string, error)
}

func NewDiscoverer() *Discoverer {
	return &Discoverer{
		ExecLookPath: exec.LookPath,
	}
}

type mockExecProxy struct {
	commandFn  func(name string, arg ...string) *exec.Cmd
	lookPathFn func(file string) (string, error)
}

func (m mockExecProxy) Command(name string, arg ...string) *exec.Cmd {
	return m.commandFn(name, arg...)
}

func (m mockExecProxy) LookPath(file string) (string, error) {
	if m.lookPathFn == nil {
		return "/mock/" + file, nil
	}
	return m.lookPathFn(file)
}

type execProxy interface {
	Command(name string, arg ...string) *exec.Cmd
	LookPath(file string) (string, error)
}

type realExecProxy struct{}

var ExecCommand = exec.Command

func (realExecProxy) Command(name string, arg ...string) *exec.Cmd {
	return ExecCommand(name, arg...)
}

func (realExecProxy) LookPath(file string) (string, error) {
	return exec.LookPath(file)
}

```

Note DO not use a global this is to avoid the use of globals. Ie:
```
var osExec execProxy = realExecProxy{} // wrong
```

Is wrong it defeats the purpose

```
func TestGenerate_Paths(t *testing.T) {
	fs := fstest.MapFS{
		"go.mod":      &fstest.MapFile{Data: []byte("module example.com/test\n\ngo 1.22\n")},
		"main.go":     &fstest.MapFile{Data: []byte(`package main
// Root is a subcommand ` + "`app`" + `
func Root() {}
`)},
		"pkg1/cmd.go": &fstest.MapFile{Data: []byte(`package pkg1
// Cmd1 is a subcommand ` + "`app cmd1`" + `
func Cmd1() {}
`)},
		"pkg2/cmd.go": &fstest.MapFile{Data: []byte(`package pkg2
// Cmd2 is a subcommand ` + "`app cmd2`" + `
func Cmd2() {}
`)},
	}

	// Test with specific path
	writer := NewCollectingFileWriter()
	err := GenerateWithFS(fs, writer, ".", "", "commentv1", &parsers.ParseOptions{
		SearchPaths: []string{"pkg1"},
		Recursive:   true,
	}, false)
	if err != nil {
		t.Fatalf("Generate failed: %v", err)
	}

	if _, ok := writer.Files["cmd/app/cmd1.go"]; !ok {
		t.Errorf("Expected cmd1.go to be generated")
	}
	if _, ok := writer.Files["cmd/app/cmd2.go"]; ok {
		t.Errorf("Expected cmd2.go NOT to be generated")
	}
}

```

Obviously not limited to FS related things. But as a result Iw ould like to expand the standard library to support more such as in:



