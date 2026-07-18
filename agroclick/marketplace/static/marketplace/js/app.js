// Simple frontend interactions for AgroClick
document.addEventListener('DOMContentLoaded', function(){
	// Auto-focus search input if present
	var search = document.getElementById('busqueda');
	if(search) search.focus();

	// Clear form fields for elements with `.btn-clear`
	document.querySelectorAll('.btn-clear').forEach(function(btn){
		btn.addEventListener('click', function(e){
			e.preventDefault();
			var form = btn.closest('form');
			if(!form) return;
			form.querySelectorAll('input[type="text"], input[type="number"], textarea').forEach(function(i){ i.value = ''; });
			form.querySelectorAll('select').forEach(function(s){ s.selectedIndex = 0; });
		});
	});

	// Simple form validation helper: mark empty required inputs
	document.querySelectorAll('form').forEach(function(form){
		form.addEventListener('submit', function(e){
			var required = form.querySelectorAll('[required]');
			var invalid = false;
			required.forEach(function(inp){
				if(!inp.value){
					invalid = true;
					inp.style.outline = '2px solid rgba(244,67,54,0.24)';
				}
			});
			if(invalid){
				// allow server-side handling but optionally prevent immediate submit
				// e.preventDefault();
			}
		});
	});

	// Toast helper
	function showToast(msg){
		var t = document.createElement('div');
		t.className = 'gc-toast';
		t.textContent = msg;
		document.body.appendChild(t);
		// force reflow
		void t.offsetWidth;
		t.classList.add('show');
		setTimeout(function(){ t.classList.remove('show'); setTimeout(function(){ t.remove(); },300); },2000);
	}

	// Add-to-cart visual interaction (demo)
	document.addEventListener('click', function(e){
		var btn = e.target.closest && e.target.closest('.btn-add');
		if(!btn) return;
		e.preventDefault();
		var name = btn.getAttribute('data-name') || 'Producto';
		// small click animation
		btn.classList.add('clicked');
		setTimeout(function(){ btn.classList.remove('clicked'); },220);
		showToast(name + ' agregado');
	});

	// Password toggle for login
	document.addEventListener('click', function(e){
		var t = e.target.closest && e.target.closest('.password-toggle');
		if(!t) return;
		var wrapper = t.closest('.input-with-icon');
		if(!wrapper) return;
		var input = wrapper.querySelector('input[type="password"], input[type="text"]');
		if(!input) return;
		if(input.type === 'password'){
			input.type = 'text';
			t.textContent = 'Ocultar';
			t.setAttribute('aria-label','Ocultar contraseña');
		} else {
			input.type = 'password';
			t.textContent = 'Mostrar';
			t.setAttribute('aria-label','Mostrar contraseña');
		}
	});

});
