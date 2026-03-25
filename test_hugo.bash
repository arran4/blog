#!/bin/bash
wget -qO hugo.tar.gz https://github.com/gohugoio/hugo/releases/download/v0.124.1/hugo_extended_0.124.1_linux-amd64.tar.gz
tar -xzf hugo.tar.gz hugo
sudo mv hugo /usr/local/bin/
rm hugo.tar.gz
hugo version
