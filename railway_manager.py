# ========================================
# railway_manager.py - GESTOR AVANZADO DE DEPLOYMENTS
# Para administrar los 3 sistemas en Railway
# ========================================

import os
import json
import subprocess
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path

class RailwayManager:
    """Gestor avanzado para administrar deployments en Railway"""
    
    def __init__(self):
        self.projects = {
            "sincrono": {
                "name": "Sistema Síncrono",
                "emoji": "⚡",
                "git_branch": "main-sincrono",
                "railway_url": None,  # Se configurará después del deploy
                "status": "unknown"
            },
            "asincrono": {
                "name": "Sistema Asíncrono", 
                "emoji": "🔄",
                "git_branch": "main-asincrono",
                "railway_url": None,
                "status": "unknown"
            },
            "hibrido": {
                "name": "Sistema Híbrido",
                "emoji": "🔀", 
                "git_branch": "main-hibrido",
                "railway_url": None,
                "status": "unknown"
            }
        }
        
        self.base_dir = Path.cwd()
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.config_file = self.base_dir / "railway_config.json"
        self._load_config()
    
    def _load_config(self):
        """Cargar configuración guardada"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    for project_key, project_config in config.get('projects', {}).items():
                        if project_key in self.projects:
                            self.projects[project_key].update(project_config)
            except Exception as e:
                print(f"⚠️ Error cargando configuración: {e}")
    
    def _save_config(self):
        """Guardar configuración"""
        try:
            config = {
                'projects': self.projects,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"⚠️ Error guardando configuración: {e}")
    
    def status_all_projects(self):
        """Verificar estado de todos los proyectos"""
        
        print("📊 ESTADO DE TODOS LOS PROYECTOS")
        print("=" * 60)
        
        for project_key, project_info in self.projects.items():
            print(f"\n{project_info['emoji']} {project_info['name']}")
            print("-" * 40)
            
            self.check_project_status(project_key)
    
    def check_project_status(self, project_key):
        """Verificar estado de un proyecto específico"""
        
        project_info = self.projects[project_key]
        deploy_dir = self.base_dir / f"deploy_{project_key}"
        
        # Verificar directorio de deploy
        if deploy_dir.exists():
            print(f"📁 Directorio deploy: ✅ Existe")
            
            # Verificar archivos críticos
            archivos_criticos = ['app.py', 'requirements.txt', 'railway.json']
            archivos_ok = all((deploy_dir / archivo).exists() for archivo in archivos_criticos)
            
            print(f"📄 Archivos críticos: {'✅ OK' if archivos_ok else '❌ Faltantes'}")
            
            # Verificar si es un repositorio git
            git_status = self.check_git_status(deploy_dir)
            print(f"📋 Git status: {git_status}")
            
            # Intentar verificar URL de Railway si está configurada
            if project_info.get('railway_url'):
                railway_status = self.check_railway_health(project_info['railway_url'])
                print(f"🚂 Railway status: {railway_status}")
            else:
                print(f"🚂 Railway URL: ⚠️ No configurada")
        
        else:
            print(f"📁 Directorio deploy: ❌ No existe")
            print(f"💡 Ejecuta: python deploy_to_railway.py {project_key}")
    
    def check_git_status(self, project_dir):
        """Verificar estado de git en el directorio"""
        
        try:
            os.chdir(project_dir)
            
            # Verificar si es repo git
            result = subprocess.run(['git', 'status'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Verificar si hay cambios sin commit
                if "nothing to commit" in result.stdout:
                    return "✅ Limpio"
                elif "Changes not staged" in result.stdout:
                    return "⚠️ Cambios sin commit"
                else:
                    return "📝 Cambios listos para commit"
            else:
                return "❌ No es repo git"
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
        
        finally:
            os.chdir(self.base_dir)
    
    def check_railway_health(self, url):
        """Verificar salud de la aplicación en Railway"""
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                return "✅ Activo"
            else:
                return f"⚠️ HTTP {response.status_code}"
        
        except requests.exceptions.Timeout:
            return "⏱️ Timeout"
        except requests.exceptions.ConnectionError:
            return "❌ No conecta"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def deploy_project_with_git(self, project_key, commit_message=None):
        """Deployar proyecto usando git"""
        
        project_info = self.projects[project_key]
        deploy_dir = self.base_dir / f"deploy_{project_key}"
        
        if not deploy_dir.exists():
            print(f"❌ Directorio {deploy_dir} no existe")
            print(f"💡 Ejecuta primero: python deploy_to_railway.py {project_key}")
            return False
        
        try:
            os.chdir(deploy_dir)
            
            print(f"🚀 Deploying {project_info['emoji']} {project_info['name']}")
            print("-" * 50)
            
            # 1. Inicializar git si no existe
            if not (deploy_dir / '.git').exists():
                print("📋 Inicializando repositorio git...")
                subprocess.run(['git', 'init'], check=True)
                subprocess.run(['git', 'branch', '-M', 'main'], check=True)
            
            # 2. Agregar archivos
            print("📄 Agregando archivos...")
            subprocess.run(['git', 'add', '.'], check=True)
            
            # 3. Commit
            if commit_message is None:
                commit_message = f"Deploy {project_info['name']} {self.timestamp}"
            print(f"📝 Commit: {commit_message}")
            
            # Verificar si hay cambios para commit
            result = subprocess.run(['git', 'diff', '--staged'], 
                                  capture_output=True, text=True)
            
            if result.stdout.strip():
                subprocess.run(['git', 'commit', '-m', commit_message], check=True)
                print("✅ Commit realizado")
            else:
                print("⚠️ No hay cambios para commit")
            
            # 4. Conectar con Railway (si no está conectado)
            if not self._is_railway_connected():
                print("🔗 Conectando con Railway...")
                result = subprocess.run(['railway', 'login'], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    print("❌ Error conectando con Railway")
                    return False
            
            # 5. Crear proyecto en Railway si no existe
            railway_project = self._get_railway_project_name(project_key)
            if not self._railway_project_exists(railway_project):
                print(f"🆕 Creando proyecto en Railway: {railway_project}")
                subprocess.run(['railway', 'create', railway_project], check=True)
            
            # 6. Deployar
            print("🚂 Deploying a Railway...")
            result = subprocess.run(['railway', 'up'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Deploy exitoso!")
                
                # Obtener URL del deployment
                url = self._get_railway_url()
                if url:
                    self.projects[project_key]['railway_url'] = url
                    self.projects[project_key]['status'] = 'active'
                    self._save_config()
                    print(f"🌐 URL: {url}")
                
                return True
            else:
                print(f"❌ Error en deploy: {result.stderr}")
                return False
        
        except subprocess.CalledProcessError as e:
            print(f"❌ Error ejecutando comando: {e}")
            return False
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return False
        
        finally:
            os.chdir(self.base_dir)
    
    def _is_railway_connected(self):
        """Verificar si Railway CLI está conectado"""
        try:
            result = subprocess.run(['railway', 'whoami'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _get_railway_project_name(self, project_key):
        """Generar nombre único para el proyecto en Railway"""
        return f"sistema-{project_key}-{self.timestamp[:8]}"
    
    def _railway_project_exists(self, project_name):
        """Verificar si el proyecto existe en Railway"""
        try:
            result = subprocess.run(['railway', 'list'], 
                                  capture_output=True, text=True, timeout=10)
            return project_name in result.stdout
        except:
            return False
    
    def _get_railway_url(self):
        """Obtener URL del deployment en Railway"""
        try:
            result = subprocess.run(['railway', 'domain'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'https://' in line:
                        return line.strip()
        except:
            pass
        return None
    
    def redeploy_all(self):
        """Redesplegar todos los proyectos"""
        print("🔄 REDESPLIEGUE MASIVO")
        print("=" * 50)
        
        resultados = {}
        
        for project_key in self.projects.keys():
            print(f"\n🚀 Redespliegue: {project_key}")
            resultado = self.deploy_project_with_git(
                project_key, 
                f"Redeploy masivo {self.timestamp}"
            )
            resultados[project_key] = resultado
            
            if resultado:
                print(f"✅ {project_key} redespliegue exitoso")
            else:
                print(f"❌ {project_key} redespliegue falló")
            
            # Pausa entre deployments
            time.sleep(5)
        
        # Resumen final
        print("\n📊 RESUMEN DE REDESPLIEGUE")
        print("-" * 40)
        exitosos = sum(1 for r in resultados.values() if r)
        fallidos = len(resultados) - exitosos
        
        print(f"✅ Exitosos: {exitosos}")
        print(f"❌ Fallidos: {fallidos}")
        
        return resultados
    
    def rollback_project(self, project_key, steps=1):
        """Hacer rollback de un proyecto"""
        project_info = self.projects[project_key]
        deploy_dir = self.base_dir / f"deploy_{project_key}"
        
        if not deploy_dir.exists():
            print(f"❌ Directorio {deploy_dir} no existe")
            return False
        
        try:
            os.chdir(deploy_dir)
            
            print(f"⏪ Rollback {project_info['emoji']} {project_info['name']}")
            print(f"📝 Retrocediendo {steps} commit(s)")
            
            # Hacer rollback en git
            subprocess.run(['git', 'reset', '--hard', f'HEAD~{steps}'], check=True)
            
            # Redesplegar
            result = subprocess.run(['railway', 'up'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Rollback exitoso!")
                return True
            else:
                print(f"❌ Error en rollback: {result.stderr}")
                return False
        
        except Exception as e:
            print(f"❌ Error en rollback: {e}")
            return False
        
        finally:
            os.chdir(self.base_dir)
    
    def update_railway_url(self, project_key, url):
        """Actualizar URL de Railway manualmente"""
        if project_key in self.projects:
            self.projects[project_key]['railway_url'] = url
            self._save_config()
            print(f"✅ URL actualizada para {project_key}: {url}")
        else:
            print(f"❌ Proyecto {project_key} no encontrado")
    
    def show_logs(self, project_key, lines=50):
        """Mostrar logs de Railway"""
        deploy_dir = self.base_dir / f"deploy_{project_key}"
        
        if not deploy_dir.exists():
            print(f"❌ Directorio {deploy_dir} no existe")
            return
        
        try:
            os.chdir(deploy_dir)
            print(f"📋 Logs del proyecto {project_key} (últimas {lines} líneas)")
            print("-" * 50)
            
            result = subprocess.run(['railway', 'logs', '--tail', str(lines)], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(result.stdout)
            else:
                print(f"❌ Error obteniendo logs: {result.stderr}")
        
        except Exception as e:
            print(f"❌ Error: {e}")
        
        finally:
            os.chdir(self.base_dir)

def main():
    """Función principal para usar desde línea de comandos"""
    import sys
    
    manager = RailwayManager()
    
    if len(sys.argv) < 2:
        print("🚂 RAILWAY MANAGER - Gestor de Deployments")
        print("=" * 50)
        print("Uso:")
        print("  python railway_manager.py status                    # Estado de todos")
        print("  python railway_manager.py status <proyecto>         # Estado específico")
        print("  python railway_manager.py deploy <proyecto>         # Deploy proyecto")
        print("  python railway_manager.py redeploy-all              # Redesplegar todos")
        print("  python railway_manager.py rollback <proyecto> [steps] # Rollback")
        print("  python railway_manager.py logs <proyecto> [lines]   # Ver logs")
        print("  python railway_manager.py url <proyecto> <url>      # Actualizar URL")
        print("\nProyectos disponibles:")
        for key, info in manager.projects.items():
            print(f"  {info['emoji']} {key} - {info['name']}")
        return
    
    comando = sys.argv[1].lower()
    
    if comando == "status":
        if len(sys.argv) == 3:
            project_key = sys.argv[2]
            if project_key in manager.projects:
                manager.check_project_status(project_key)
            else:
                print(f"❌ Proyecto '{project_key}' no encontrado")
        else:
            manager.status_all_projects()
    
    elif comando == "deploy":
        if len(sys.argv) >= 3:
            project_key = sys.argv[2]
            if project_key in manager.projects:
                manager.deploy_project_with_git(project_key)
            else:
                print(f"❌ Proyecto '{project_key}' no encontrado")
        else:
            print("❌ Especifica el proyecto a deployar")
    
    elif comando == "redeploy-all":
        manager.redeploy_all()
    
    elif comando == "rollback":
        if len(sys.argv) >= 3:
            project_key = sys.argv[2]
            steps = int(sys.argv[3]) if len(sys.argv) >= 4 else 1
            if project_key in manager.projects:
                manager.rollback_project(project_key, steps)
            else:
                print(f"❌ Proyecto '{project_key}' no encontrado")
        else:
            print("❌ Especifica el proyecto para rollback")
    
    elif comando == "logs":
        if len(sys.argv) >= 3:
            project_key = sys.argv[2]
            lines = int(sys.argv[3]) if len(sys.argv) >= 4 else 50
            if project_key in manager.projects:
                manager.show_logs(project_key, lines)
            else:
                print(f"❌ Proyecto '{project_key}' no encontrado")
        else:
            print("❌ Especifica el proyecto para ver logs")
    
    elif comando == "url":
        if len(sys.argv) >= 4:
            project_key = sys.argv[2]
            url = sys.argv[3]
            manager.update_railway_url(project_key, url)
        else:
            print("❌ Especifica proyecto y URL")
    
    else:
        print(f"❌ Comando '{comando}' no reconocido")

if __name__ == "__main__":
    main()