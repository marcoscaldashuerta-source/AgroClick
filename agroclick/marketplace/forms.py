from django import forms
from .models import Producto, Perfil, TicketSoporte, SolicitudEntrega
from .models import PaymentProof
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

class CustomAuthenticationForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'Por favor ingresa un usuario y contraseña correctos. Ten en cuenta que ambos campos distinguen mayúsculas y minúsculas.',
        'inactive': 'Esta cuenta no está activa.',
        'vendedor_no_aprobado': 'Tu cuenta de vendedor aún está en revisión. No puedes acceder a funciones de vendedor hasta que un administrador apruebe tu solicitud.',
    }

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        try:
            perfil = Perfil.objects.get(usuario=user)
        except Perfil.DoesNotExist:
            return

        if perfil.rol == 'vendedor' and not perfil.aprobado:
            raise ValidationError(
                self.error_messages['vendedor_no_aprobado'],
                code='vendedor_no_aprobado'
            )

class RegistroForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        error_messages={
            'required': 'El nombre de usuario es obligatorio.',
            'max_length': 'El nombre de usuario no puede superar los 150 caracteres.'
        }
    )
    email = forms.EmailField(
        error_messages={
            'required': 'El correo electrónico es obligatorio.',
            'invalid': 'Introduce una dirección de correo válida.'
        }
    )

    password = forms.CharField(
        widget=forms.PasswordInput,
        error_messages={'required': 'La contraseña es obligatoria.'}
    )

    ROL_CHOICES = [
        ('comprador', 'Comprador'),
        ('vendedor', 'Vendedor'),
    ]

    rol = forms.ChoiceField(
        choices=ROL_CHOICES,
        error_messages={'required': 'Selecciona un rol.'}
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('El nombre de usuario ya está en uso. Elige otro.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Ya existe una cuenta con ese correo electrónico.')
        return email

class ProductoForm(forms.ModelForm):

    CATEGORIA_CHOICES = [
        ('Fruta', 'Fruta'),
        ('Verdura', 'Verdura'),
    ]

    categoria = forms.ChoiceField(
        choices=CATEGORIA_CHOICES,
        error_messages={'required': 'Selecciona una categoría.'}
    )

    def __init__(self, *args, **kwargs):
        self.saving_draft = kwargs.pop('saving_draft', False)
        super().__init__(*args, **kwargs)
        if self.saving_draft:
            for field_name in ['categoria', 'descripcion', 'precio', 'unidad_venta', 'stock', 'imagen', 'imagen2', 'imagen3', 'imagen4', 'imagen5']:
                if field_name in self.fields:
                    self.fields[field_name].required = False
            if 'nombre' in self.fields:
                self.fields['nombre'].required = False

    def clean(self):
        cleaned_data = super().clean()
        if self.saving_draft:
            return cleaned_data

        files = self.files.getlist('images')
        has_uploaded_image = bool(files)

        existing_instance = getattr(self, 'instance', None)
        has_existing_image = False
        if existing_instance is not None:
            if getattr(existing_instance, 'pk', None) is not None:
                has_existing_image = bool(getattr(existing_instance, 'imagen', None)) or existing_instance.imagenes.exists()
            else:
                has_existing_image = bool(getattr(existing_instance, 'imagen', None))
        elif cleaned_data.get('imagen'):
            has_existing_image = True

        if has_uploaded_image or has_existing_image:
            return cleaned_data

        raise ValidationError('Debes agregar al menos una imagen antes de publicar o guardar el producto.')

    class Meta:
        model = Producto

        fields = [
            'nombre',
            'categoria',
            'descripcion',
            'precio',
            'unidad_venta',
            'stock',
            'imagen',
            'imagen2',
            'imagen3',
            'imagen4',
            'imagen5'
        ]
        error_messages = {
            'nombre': {
                'required': 'El nombre del producto es obligatorio.',
                'max_length': 'El nombre del producto no puede superar los 60 caracteres.'
            },
            'descripcion': {'required': 'La descripción del producto es obligatoria.'},
            'precio': {
                'required': 'El precio es obligatorio.',
                'invalid': 'Ingresa un precio válido.'
            },
            'unidad_venta': {'required': 'La unidad de venta es obligatoria.'},
            'stock': {
                'required': 'El stock es obligatorio.',
                'invalid': 'Ingresa una cantidad válida.'
            },
            'imagen': {'invalid': 'La imagen principal no es válida.'},
            'imagen2': {'invalid': 'La segunda imagen no es válida.'},
            'imagen3': {'invalid': 'La tercera imagen no es válida.'},
            'imagen4': {'invalid': 'La cuarta imagen no es válida.'},
            'imagen5': {'invalid': 'La quinta imagen no es válida.'},
        }


class TicketSoporteForm(forms.ModelForm):
    """Formulario dinámico de soporte: el usuario se toma de la sesión,
    la persona solo completa razón y descripción."""

    razon = forms.ChoiceField(
        choices=TicketSoporte.RAZON_CHOICES,
        label='Razón',
        error_messages={'required': 'Selecciona una razón para tu solicitud.'}
    )

    descripcion = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'Cuéntanos con detalle qué sucede...'}),
        label='Descripción',
        error_messages={'required': 'Describe brevemente tu solicitud.'}
    )

    class Meta:
        model = TicketSoporte
        fields = ['razon', 'descripcion']


class EntregaForm(forms.ModelForm):
    """Formulario para elegir el método de entrega al proceder al pago."""

    tipo_entrega = forms.ChoiceField(
        choices=SolicitudEntrega.TIPO_ENTREGA_CHOICES,
        widget=forms.RadioSelect,
        label='Método de entrega',
        error_messages={'required': 'Selecciona un método de entrega.'}
    )

    direccion_entrega = forms.CharField(
        required=False,
        max_length=255,
        label='Dirección de entrega',
        widget=forms.TextInput(attrs={'placeholder': 'Calle, número, comuna...'})
    )

    referencia = forms.CharField(
        required=False,
        max_length=255,
        label='Referencia adicional (opcional)',
        widget=forms.TextInput(attrs={'placeholder': 'Ej: casa color azul, depto 302...'})
    )

    tipo_pago = forms.ChoiceField(
        choices=SolicitudEntrega.TIPO_PAGO_CHOICES,
        widget=forms.RadioSelect,
        label='Método de pago',
        error_messages={'required': 'Selecciona un método de pago.'}
    )

    class Meta:
        model = SolicitudEntrega
        fields = ['tipo_entrega', 'direccion_entrega', 'referencia', 'tipo_pago']

    def clean(self):
        cleaned_data = super().clean()
        tipo_entrega = cleaned_data.get('tipo_entrega')
        direccion_entrega = cleaned_data.get('direccion_entrega')

        if tipo_entrega == 'delivery' and not direccion_entrega:
            self.add_error('direccion_entrega', 'Indica la dirección de entrega para el Delivery.')

        return cleaned_data


class PaymentProofForm(forms.ModelForm):
    class Meta:
        model = PaymentProof
        fields = ['imagen']