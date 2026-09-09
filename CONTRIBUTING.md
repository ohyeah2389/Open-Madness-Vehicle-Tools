# Contributing

Contributions are welcome, but there are a few things you must know before you open a pull request:

## Licensing of contributions

You keep the copyright in what you write. By contributing, you agree that your contribution is licensed under GPL-3.0-or-later with the [output exception](LICENSE-EXCEPTION.txt).

There is no copyright assignment and no CLA.

## Developer Certificate of Origin

Every commit must be signed off, certifying that you have the right to submit it. Add a sign-off with `git commit -s`, which appends:

```
Signed-off-by: Your Name <your.email@example.com>
```

Sign-off certifies the Developer Certificate of Origin 1.1:

```
By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I have the right to submit it under the open source license indicated in the file; or

(b) The contribution is based upon previous work that, to the best of my knowledge, is covered under an appropriate open source license and I have the right under that license to submit that work with modifications, whether created in whole or in part by me, under the same license (unless I am permitted to submit under a different license), as indicated in the file; or

(c) The contribution was provided directly to me by some other person who certified (a), (b) or (c) and I have not modified it.

(d) I understand and agree that this project and the contribution are public and that a record of the contribution (including all personal information I submit with it, including my sign-off) is maintained indefinitely and may be redistributed consistent with this project or the open source license(s) involved.
```

The full text is at <https://developercertificate.org/>.

## Do not contribute extracted game content

This project documents and targets a closed-source engine, so it has to be careful about what it ships. Do not add files extracted from any game, including meshes, textures, sounds, physics binaries, packed archives, or unpacked physics parameter files. Documenting a file format is fine; redistributing the contents of those files is not.

`physics/names.json` is a list of short identifier tokens used to reverse hashes. It does not constitute vehicle physics data.
