$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
git apply .\admin_arch_cleanup_utf8_bom.patch
