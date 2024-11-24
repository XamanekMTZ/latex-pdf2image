from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import FileResponse
import os
import subprocess
from pdf2image import convert_from_path
import time

app = FastAPI()

class LatexRequest(BaseModel):
    latex_code: str
    filename: str
    dpi: int = 600  # Valor predeterminado de 600 DPI

class LatexToImage:
    def __init__(self, latex_code: str):
        self.latex_code = latex_code

    def generate_image(self, filename: str, dpi: int, output_dir: str = "/app/images"):
        # Crea el directorio de salida si no existe
        os.makedirs(output_dir, exist_ok=True)

        # Genera un nombre de archivo único usando el timestamp UNIX
        timestamp = int(time.time())
        output_filename = f"{output_dir}/{filename}_{dpi}_{timestamp}.png"
        tex_filename = f"{output_dir}/{filename}_{dpi}_{timestamp}.tex"
        pdf_filename = f"{output_dir}/{filename}_{dpi}_{timestamp}.pdf"
        
        # Guarda el código LaTeX en un archivo temporal
        with open(tex_filename, "w") as f:
            f.write(self.latex_code)

        # Ejecuta pdflatex para generar un PDF a partir del código LaTeX
        result = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-output-directory", output_dir, tex_filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(result.stderr.decode())  # Muestra el error de pdflatex
            #raise RuntimeError(f"Error al ejecutar pdflatex. Revisa el código LaTeX o las dependencias.")
        
        # Verifica que el archivo PDF fue generado
        if not os.path.exists(pdf_filename):
            raise RuntimeError("No se generó el archivo PDF. Verifica el código LaTeX.")
        
        # Intenta convertir el PDF a imagen usando pdf2image y especifica la ruta de pdftoppm
        try:
            images = convert_from_path(pdf_filename, dpi=dpi, poppler_path="/usr/bin")
            if not images:
                raise RuntimeError("pdf2image no generó ninguna imagen.")
            images[0].save(output_filename, "PNG")
        except Exception as e:
            raise RuntimeError(f"Error al convertir PDF a imagen: {e}")
        
        return output_filename

@app.post("/generate-image")
async def generate_image_endpoint(request: LatexRequest):
    latex_to_image = LatexToImage(request.latex_code)
    try:
        output_file = latex_to_image.generate_image(filename=request.filename, dpi=request.dpi)
        
        # Envía el archivo generado sin eliminarlo
        return FileResponse(output_file, media_type="image/png", filename=os.path.basename(output_file))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
