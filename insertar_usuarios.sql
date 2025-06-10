
-- Usuario con SHA256 simple
DELETE FROM usuarios WHERE username = 'direct1';
INSERT INTO usuarios (username, email, password_hash, salt, nombre_completo, rol, activo) 
VALUES ('direct1', 'direct1@temp.com', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3', '', 'Usuario Directo 1', 'SUPERUSUARIO', true);

-- Usuario con MD5 simple
DELETE FROM usuarios WHERE username = 'direct2';
INSERT INTO usuarios (username, email, password_hash, salt, nombre_completo, rol, activo)
VALUES ('direct2', 'direct2@temp.com', '202cb962ac59075b964b07152d234b70', '', 'Usuario Directo 2', 'SUPERUSUARIO', true);

-- Usuario con hash conocido
DELETE FROM usuarios WHERE username = 'direct3';
INSERT INTO usuarios (username, email, password_hash, salt, nombre_completo, rol, activo)
VALUES ('direct3', 'direct3@temp.com', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3', 'hello', 'Usuario Directo 3', 'SUPERUSUARIO', true);
