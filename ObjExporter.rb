#-----------------------------------------------------------------------------
#
# WaveFront .Obj File Exporter for Google SketchUp
# Author: M van der Honing, mvdhoning@noeska.com
#	  
# Based on ZbylsXExporter by Zbigniew Skowron, zbychs@gmail.com
#
# I'd like to thank Jonathan Harris and Erwan de Cadoudal for their exporters.
# They helped me a lot.
#
#-----------------------------------------------------------------------------

module ObjExporter

module_function

Meter_to_inch = 39.3700787
Inch_to_meter = 1.0 / Meter_to_inch

#-----------------------------------------------------------------------------

def reload
	pfile = Sketchup.find_support_file "ObjExporter.rb", "Plugins"
	load pfile
end

#-----------------------------------------------------------------------------

def obj_header()
	text = "#Exported from google sketchup"
end

#-----------------------------------------------------------------------------

def directx_def_material()

#Ka
#Kd
#Ks
#Ns

text = "newmtl Default_Material 
Ka 0.000000 0.000000 0.000000
Kd 1.0 1.0 1.0 
Tr 1.0
Ks 0.000000 0.000000 0.000000
Ns 3.2
"
end

#-----------------------------------------------------------------------------

def directx_material(name, color, textureFile, alpha)
# #{color.red / 255.0};#{color.green / 255.0};#{color.blue / 255.0};#{color.alpha / 255.0};;
	col = format("%8.4f %8.4f %8.4f", 1.0, 1.0, 1.0)
	if !textureFile
		col = format("%8.4f %8.4f %8.4f",
				 color.red / 255.0, color.green / 255.0, color.blue / 255.0)
	end
	specular = format("%8.4f", 3.2)
	tex = ""
	tex = "   map_Kd #{textureFile}" if textureFile
	
	text = "newmtl #{name}
   Ka 0.000000 0.000000 0.000000
   Kd #{col}
   Tr #{alpha/255.0}
   Ks 0.000000 0.000000 0.000000
   Ns #{specular}
#{tex}

"
end

#-----------------------------------------------------------------------------

def out_tab(f, points, del = "", extra = "")
	cnt = points.size
	return if cnt < 1
	
	for i in 0..(cnt - 2)
		p = points[i]
		f.puts("  #{p}#{del}")
	end
		p = points[cnt - 1]
		f.puts("  #{p}#{extra}")

	f.puts("#  #{cnt} elements")
end

#-----------------------------------------------------------------------------

def out_point(p)
	print "Kuozaa Too!\n" if (!p)
	return "nil" if (!p)
	px = p.x * Inch_to_meter
	py = p.z * Inch_to_meter
	pz = p.y * Inch_to_meter
	#text = "#{px.inspect};#{py.inspect};#{pz.inspect};"
	text = format("v %8.4f %8.4f %8.4f", px, py, pz)
end

#-----------------------------------------------------------------------------
 
def out_normal(p)
	print "Kuozaa Noo!\n" if (!p)
	return "nil" if (!p)
	px = p.x
	py = p.z
	pz = p.y
	#text = "#{p.x.inspect};#{p.y.inspect};#{p.z.inspect};"
	text = format("vn %8.4f %8.4f %8.4f", px, py, pz)
end

#-----------------------------------------------------------------------------
 
def out_uv(u, v)
	#text = "#{u.inspect},#{v.inspect};"
	text = format("vt %8.4f %8.4f 0.0000", u, v)
end

#-----------------------------------------------------------------------------

#TODO: support toevoegen voor uv en normal indices
def out_face(f, face)
	face = face.reverse
	cnt = face.size
	#return if cnt < 3
	#f.printf("  #{cnt};")

#check if material change is needed

#mats = []
#	for n, mat in materials
#		mats.push(n)
#	end

#m = face[1]
#midx = mats.index(m)
#f.puts("mat  #{midx};")

f.printf("f ")
	for i in 0..(cnt - 2)
		p = face[i]
		f.printf("#{p[0]+1}/#{p[1]+1}/#{p[2]+1} ")
	end
		p = face[cnt - 1]
		f.printf("#{p[0]+1}/#{p[1]+1}/#{p[2]+1}")
end

#-----------------------------------------------------------------------------
 
def out_faces(f, faces, materials)
pm = ""
        mats = []
	for n, mat in materials
		mats.push(n)
	end

	cnt = faces.size
	return if cnt < 1
	f.puts("#  #{cnt} faces")
	for i in 0..(cnt - 2)
		fc = faces[i]

m = fc[1]

if m!=pm then
	f.puts("usemtl #{m}")
	pm = m
end

		out_face(f, fc[0]);
		f.puts("")
	end
		fc = faces[cnt - 1]
		out_face(f, fc[0]);
		#out_face_ns(f, fc[0]);
#		f.puts(";;")
end

#-----------------------------------------------------------------------------
 
def out_face_ns(f, face)
	face = face.reverse
	cnt = face.size
	#return if cnt < 3
	f.printf("  #{cnt};")
	for i in 0..(cnt - 2)
		p = face[i]
		f.printf("#{p[2]},")
	end
		p = face[cnt - 1]
		f.printf("#{p[2]}")
end
#-----------------------------------------------------------------------------
 
def out_normals(f, faces)
	cnt = faces.size
	return if cnt < 1
	f.puts("  #{cnt};")
	for i in 0..(cnt - 2)
		fc = faces[i]
		out_face_ns(f, fc[0]);
		f.puts(";")
	end
		fc = faces[cnt - 1]
		out_face_ns(f, fc[0]);
		f.puts(";;")
end

#-----------------------------------------------------------------------------
 
def out_face_materials(f, faces, materials)
	#mats = materials.keys #is this ok?
	mats = []
	for n, mat in materials
		mats.push(n)
	end
	f.puts("  #{mats.size};")
	cnt = faces.size
	return if cnt < 1
	f.puts("  #{cnt};")
	for i in 0..(cnt - 2)
		fc = faces[i]
		m = fc[1]
		midx = mats.index(m)
		f.puts("  #{midx},")
	end
		fc = faces[cnt - 1]
		m = fc[1]
		midx = mats.index(m)
		f.puts("  #{midx};")
		
	mats.each { |m|
		f.puts("   { #{m} }")
	}
end

#-----------------------------------------------------------------------------
 
def out_materials(f, materials)
	for n, mat in materials
		if n == "Default_Material"
			f.puts(directx_def_material())
		else
			f.puts(directx_material(mat[0], mat[1], mat[2], mat[3]));
		end
	end
end

#-----------------------------------------------------------------------------

def processFileName(fname)
	slash = "\\"
	dir = "c:\\temp"
	sidx = fname.rindex(slash)
	if (!sidx)
		slash = "/"
		dir = "/tmp"
		sidx = fname.rindex(slash)
	end
	name = "Untitled.obj"
	if (sidx)
		dir = fname[0..(sidx-1)]
		name = fname[(sidx+1)..-1]
		didx = name.rindex('.')
		name += ".obj" if !didx
		name[didx..-1] = ".obj" if didx
	end
	
	return [name, dir, slash]
end

#-----------------------------------------------------------------------------

def exportXFileUI
	# Create the WebDialog instance

	fname = Sketchup.active_model.path
	name, dir, slash = processFileName(fname)

	my_dialog = UI::WebDialog.new(".Obj File Exporter", true, ".Obj File Exporter", 
									600, 600, 200, 200, true)

	# Attach an action callback
	my_dialog.add_action_callback("browse") { |web_dialog, params|
		#puts params
		a = params.split(',');
  		outDir = a[0]
  		outFile = a[1]
  		outDir += slash if outDir[-1] != slash[0]
		#puts(outDir, outFile)
		fname = UI.savepanel("Export to...", outDir, outFile)
		fname = UI.savepanel("Export to...") if !fname
		if fname
			name, dir, slash = processFileName(fname)
			dir = dir.gsub(/['"\\]/) { '\\'+$& }
  			my_dialog.execute_script(
				"document.getElementById('outDir').value = '#{dir}'");
  			my_dialog.execute_script(
				"document.getElementById('outFile').value = '#{name}'");
		end
	}

	my_dialog.add_action_callback("ruby") { |web_dialog, params|
		#puts params
		# display ruby panel for messages
		Sketchup.send_action "showRubyPanel:"
	}
	
	# Attach an action callback
	my_dialog.add_action_callback("export") { |web_dialog, params|
		#puts params
		a = params.split(',');
		#UI.messagebox("Ruby says: Your javascript has asked for " + a)
  		#my_dialog.execute_script(
  		#	"document.getElementById('ala').innerHTML= '#{a.to_s}'");
  		outDir = a[0]
  		outFile = a[1]
  		smartFaces = a[2] == "true"
  		front = a[3] == "true"
  		back = a[4] == "true"
  		uv = a[5] == "true"
  		sel = a[6] == "true"
  		tex = a[7] == "true"
		outName = outDir + slash + outFile

		#print(outName, outDir, outFile, smartFaces, front, back, uv, sel, tex)
  		my_dialog.execute_script(
			"document.getElementById('console').innerHTML = ''");
  		my_dialog.execute_script(
			"document.getElementById('progress').innerHTML = 'Exporting...'");
		
		res = exportXFile(outName, outDir, smartFaces, front, back, uv, sel, tex,
		lambda {|forward, text|
			if forward
				puts text
				text = text.gsub(/['"\\]/) { '\\'+$& }
				text = text.gsub(/[\n]/) { '<br>' }
				text += '<br>'
		  		my_dialog.execute_script(
  					"document.getElementById('console').innerHTML += '\\n#{text}'");
			else
				print text
		  		#my_dialog.execute_script(
  				#	"document.getElementById('progress').innerHTML += '#{text}'");
			end
		})
  		my_dialog.execute_script(
			"document.getElementById('progress').innerHTML = '#{res ? 'Exported' : 'Not exported!'}'");
	}


	html="
	<html>
	<head>
		<title>WorldEd Exporter</title>
		<script>
		function callRuby(actionName, params) {
			query = 'skp:'+ actionName + '@' + params;
			window.location.href = query;
		}
		function rubyFunc() {
			callRuby('ruby', '')
		}
		function browseFunc() {
			outputDir = document.getElementById('outDir').value
			outputFile = document.getElementById('outFile').value
			callRuby('browse', outputDir + ',' + outputFile)
		}
		function exportFunc() {
			outputDir = document.getElementById('outDir').value
			outputFile = document.getElementById('outFile').value
			smart = document.getElementById('smartFaces').checked
			front = document.getElementById('frontFaces').checked
			back = document.getElementById('backFaces').checked
			uv = document.getElementById('useUVHelper').checked
			sel = document.getElementById('exportSelected').checked
			tex = document.getElementById('exportTextured').checked
			callRuby('export', outputDir + ',' + outputFile + ',' + smart + ',' + front + ',' + back + ',' + uv + ',' + sel + ',' + tex)
		}
		</script>
	</head>
	<body>
		<input type='button' onclick='exportFunc()' value='Export .Obj File'> 
		<input type='button' onclick='rubyFunc()' value='Show Console'><br>
		<div>
		<div id='progress' style='color: red'>
		</div>
		Output directory:<br>
		<input id='outDir' type='text' value='#{dir}' size='60'><br>
		Output file: 
		<input type='button' onclick='browseFunc()' value='Browse'><br>
		<input id='outFile' type='text' value='#{name}' size='60'><br>
		<input id='smartFaces' type='checkbox' value='Smart faces' checked='checked'> Guess which faces to export<br>
		<input id='frontFaces' type='checkbox' value='Front faces'> Export front faces<br>
		<input id='backFaces' type='checkbox' value='Back faces'> Export back faces<br>
		<input id='useUVHelper' type='checkbox' value='Use UVHelper' checked='checked'> Use UVHelper<br>
		<input id='exportSelected' type='checkbox' value='Export Selected'> Export selected only<br>
		<input id='exportTextured' type='checkbox' value='Export Textured'> Export textured only<br>
		<hr>
		<div id='console' style='color: grey; font-family: monospace; font-size: smaller'>
		</div>
		</div>
	</body>
	</html>
	"
	
	#print html
	my_dialog.set_html(html)
	
	my_dialog.show {
  		#my_dialog.execute_script(
  		#	"document.getElementById('ala').innerHTML = '<b>Hi There!</b>'");
	}
end

#-----------------------------------------------------------------------------

def exportXFileEngine(entities, trans, tw,
						materials, indexer, points, uvs, normals, faces,
						smartInfo, print_callback)

  entities.each { |ent|
    next if ent.hidden? or not ent.layer.visible?

    case ent.typename
		when "ComponentInstance"
			print_callback.call(true, "Exporting Component: " + ent.definition.name + " " + ent.name)
		    exportXFileEngine(ent.definition.entities, trans*ent.transformation, tw,
							materials, indexer, points, uvs, normals, faces,
							smartInfo, print_callback)
			#print_callback.call(true, "Done.")

		when "Group"
			print_callback.call(true, "Exporting Group: " + ent.name)
		    exportXFileEngine(ent.entities, trans*ent.transformation, tw,
							materials, indexer, points, uvs, normals, faces,
							smartInfo, print_callback)
			#print_callback.call(true, "Done.")
    end
  }

	ss = entities
	ss = ss.select {|ent| 
		(ent.kind_of? Sketchup::Face) && !ent.hidden? && ent.layer.visible?
	}
	if ss.empty?
		print_callback.call(true, "Nothing to export.")
		return false
	end


	smarty = {}
	ss = ss.select {|face|
		matF = nil;
		matF = face.material
		texF = nil
		texF = matF.texture if matF

		matB = nil;
		matB = face.back_material
		texB = nil
		texB = matB.texture if matB

		smart = 0
		smart |= 1 if smartInfo["frontFaces"]
		smart |= 2 if smartInfo["backFaces"]
		
		if (smartInfo["smartFaces"])
			smart |= 1 if texF
			smart |= 2 if texB
			if smart == 0
				smart |= 1 if matF
				smart |= 2 if matB
				smart |= 3 if smart == 0
			end
		end
		
		smart &= ~1 if smartInfo["texturedOnly"] && !texF
		smart &= ~2 if smartInfo["texturedOnly"] && !texB
		
		smarty[face] = smart if smart != 0
		(smart != 0)
	}
	if ss.empty?
		print_callback.call(true, "Nothing to export: no faces chosen")
		return false
	end

	if smartInfo["textureWritePass"]
		ss.each {|face|
			[true, false].each {|front|
				if (smarty[face] & (front ? 1 : 2)) != 0
					tw.load(face, front)
				end
			}
		}
		return true
	end

	# Create transformation w/out translation for normals
	narray=trans.to_a
	narray[12..16]=[0,0,0,1]
	ntrans = Geom::Transformation.new(narray)
	
	ss.each {|face|

	  [true, false].each { |front|
	  
		print_callback.call(false, ".")
		if (smarty[face] & (front ? 1 : 2)) == 0
			next
		end
		
		mat = nil;
		mat = face.material if front
		mat = face.back_material if !front
		tex = nil
		tex = mat.texture if mat
		
		texFile = nil
		if tex
			handle = tw.handle(face, front)
			f.puts "Texture handle invalid!" if handle < 0
			texFile = tw.filename(handle).to_s
		end
		
		mname = "Default_Material"
		if mat
			mname = "_" + mat.name
			mname = mname + "-" + texFile if texFile
			mname = mname.gsub(/[^a-zA-Z0-9]/, "_")
			alpha = 255
			alpha = mat.alpha if mat.use_alpha?
			materials[mname] = [mname, mat.color, texFile, alpha]
			#puts(materials[mname])
		else
			materials[mname] = [mname, nil, nil, nil]
		end

		if tex
			uvHelp = face.get_UVHelper(true, true, tw)

			#retval = tw.write(face, front, fname + tw.filename(handle).to_s)
			#retval = (retval == FILE_WRITE_OK)
	        
			mus = []
			mvs = []
			face.outer_loop.vertices.each { |vertex|
				pos = vertex.position
				if front
					uvq = uvHelp.get_front_UVQ(pos).to_a
				else
					uvq = uvHelp.get_back_UVQ(pos).to_a
				end
			    #mus << (u.x/u.z)
			    #mvs << (u.y/u.z)
			    mus << (uvq.x)
			    mvs << (uvq.y)
			    puts "#{uvq.x} #{uvq.y} #{uvq.z}" if !(1.0-0.0001 < uvq.z && uvq.z < 1.0+0.0001)
			}
			minu = mus.min
			minv = mvs.min
			maxu = mus.max
			maxv = mvs.max
			#print("#{minu} #{minv} #{maxu} #{maxv}\n")
		end

		mesh = face.mesh 7

		#puts("Mesh:")
		for p in (1..mesh.count_polygons)
			poly = mesh.polygon_points_at(p)
			ipoly = mesh.polygons[p - 1]
			#print "Poly #{poly}\n"

			theFace = []
			
			for i in 0..(poly.size - 1)
				idx = i
				idx = (poly.size - 1) - i if !front
			
				pos = poly[idx]
				
				uq = 0.0
				vq = 0.0
				if tex
					if smartInfo["useUVHelper"]
						if front
							uvq = uvHelp.get_front_UVQ(pos).to_a
						else
							uvq = uvHelp.get_back_UVQ(pos).to_a
						end
						uq = (uvq.x)
						vq = (uvq.y)
						#printf("%8.4f %8.4f %8.4f %8.4f %8.4f %8.4f\n", uq, vq, (maxu - minu), (maxv - minv), mat.texture.width, mat.texture.height)
						#printf("%8.4f %8.4f %8.4f\n", uvq.x, uvq.y, uvq.z)
					else
						ni = ipoly[idx]
						ni = - ni if ni < 0
						uvss = mesh.uv_at(ni, 1)
						uq = uvss.x / mat.texture.width
						vq = uvss.y / mat.texture.height
						#printf("%8.4f %8.4f %8.4f\n", uvss.x, uvss.y, uvss.z)
					end
				end

				pt = out_point(trans * pos)
				uv = out_uv(uq, vq)
				
				ptuv = pt + uv					
				pidx = indexer.index(ptuv)
				if !pidx
					pidx = indexer.size
					points.push(pt) 
					uvs.push(uv) 
					indexer.push(ptuv) 
				end
				
				ni = ipoly[idx]
				ni = - ni if ni < 0
				norm = mesh.normal_at(ni)
				n = norm
				n = n.reverse if (!front)
				n = ntrans * n
				n = n.normalize
				n = out_normal(n)
				nidx = normals.index(n)
				if !nidx
					nidx = normals.size
					normals.push(n) 
				end

				theFace.push([pidx, pidx, nidx])
			end

			#puts "TheFace #{theFace}"
			faces.push([theFace, mname])
		end
	  }
	}
	print_callback.call(false, "\n")
	
	return true
end

#-----------------------------------------------------------------------------

def exportXFile(fname, outDir, smartFaces, export_front_faces, export_back_faces,
				use_uv_helper, selectedOnly, texturedOnly, print_callback)

	if !fname || !outDir
		print_callback.call(true, "Empty file or directory name.")
		return false
	end

	model = Sketchup.active_model
	ss = model.active_entities
	ss = model.selection if selectedOnly

	smartInfo = {}
	smartInfo["smartFaces"] = smartFaces
	smartInfo["frontFaces"] = export_front_faces
	smartInfo["backFaces"] = export_back_faces
	smartInfo["useUVHelper"] = use_uv_helper
	smartInfo["selectedOnly"] = selectedOnly
	smartInfo["texturedOnly"] = texturedOnly

	print_callback.call(true, "Exporting textures to: " + outDir)
    tw = Sketchup.create_texture_writer
	smartInfo["textureWritePass"] = true
	
	    exportXFileEngine(ss, Geom::Transformation.new, tw,
						nil, nil, nil, nil, nil, nil,
						smartInfo, print_callback)

    result = tw.write_all(outDir, false)
	print_callback.call(true, "Writing textures failed!") if !result
	
	print_callback.call(true, "Analyzing geometry")
	
	smartInfo["textureWritePass"] = false
	materials = {}
	indexer = []
	points = []
	uvs = []
	normals = []
	faces = []
	
		exportXFileEngine(ss, Geom::Transformation.new, tw,
						materials, indexer, points, uvs, normals, faces,
						smartInfo, print_callback)

	print_callback.call(true, "Exporting geometry to: " + fname)

	#write material file here before if needed
#TODO remove .obj
	fm = File.new (fname.gsub(".obj", ".mtl"), "w")
	fm.puts "#Materials exported from Google Sketchup"
	fm.puts ""
	out_materials(fm, materials)
	fm.close;

	#write mesh data
	f = File.new(fname, "w")
	
	f.puts(obj_header())

#TODO remove path and remove .obj
	f.puts "mtllib "+fname.gsub(outDir+"\\","").gsub(".obj", ".mtl")

#	out_materials(f, materials)
#	f.puts "Mesh mesh_0{"


	out_tab(f, points)
out_tab(f, uvs, "", "")	
out_tab(f, normals)
	

	
#	f.puts "  MeshMaterialList {"
#	out_face_materials(f, faces, materials)

#	f.puts "  }"
#	f.puts "  MeshTextureCoords {"

#	f.puts "  }"
#	f.puts "  MeshNormals {"


#	out_normals(f, faces)
	out_faces(f, faces, materials)

#	f.puts "  }"
#	f.puts "}"

	f.close	
	print_callback.call(true, "Done.")
	
	return true
end

#-----------------------------------------------------------------------------

end


if( not file_loaded?("ZbylsXExporter.rb") )
    #add_separator_to_menu("Plugins")
    plugins_menu = UI.menu("Plugins")
    plugins_menu.add_item("OBJ Exporter...") { ObjExporter.exportXFileUI }
end

file_loaded("ObjExporter.rb")

#-----------------------------------------------------------------------------

