from django import forms
from .models import Item, Message, ItemImage

class ItemForm(forms.ModelForm):
    """Ürün formu - legacy image field korundu (backward compatibility)"""
    
    class Meta:
        model = Item
        fields = ["title", "description", "category", "image"]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ürün başlığı (örn: iPhone 13 Pro)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Ürün açıklaması, durumu, özellikleri...'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'style': 'display: none;'  # Multi-upload kullanılacak
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Required alanları işaretle
        self.fields['title'].widget.attrs['required'] = True
        self.fields['category'].widget.attrs['required'] = True


class ItemImageForm(forms.ModelForm):
    """Tekil ürün görseli formu"""
    class Meta:
        model = ItemImage
        fields = ['image', 'alt_text', 'order']
        widgets = {
            'alt_text': forms.TextInput(attrs={
                'placeholder': 'Görsel açıklaması (opsiyonel)',
                'class': 'form-control'
            }),
            'order': forms.NumberInput(attrs={
                'min': 0,
                'class': 'form-control'
            })
        }

class TradeCreateForm(forms.Form):
    offered_item = forms.ModelChoiceField(queryset=Item.objects.none(), label="Teklif Ettiğin Ürün")

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["offered_item"].queryset = Item.objects.filter(owner=user)

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["content"]
        widgets = {"content": forms.Textarea(attrs={"rows": 2, "placeholder": "Mesaj yaz..."})}


class AdvancedSearchForm(forms.Form):
    """Gelişmiş arama formu"""
    
    query = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Ne arıyorsunuz? (örn: iPhone, abiye, laptop)',
            'class': 'search-input',
            'autocomplete': 'off',
            'data-autocomplete': 'true'
        }),
        label='Arama'
    )
    
    categories = forms.MultipleChoiceField(
        choices=[],  # Will be populated in __init__
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'category-checkboxes'
        }),
        label='Kategoriler'
    )
    
    conditions = forms.MultipleChoiceField(
        choices=[
            ('new', 'Sıfır'),
            ('excellent', 'Mükemmel'),
            ('good', 'İyi'),
            ('fair', 'Orta'),
            ('poor', 'Kötü'),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'condition-checkboxes'
        }),
        label='Ürün Durumu'
    )
    
    price_range = forms.ChoiceField(
        choices=[('', 'Tüm Fiyatlar')] + [
            ('0-50', '0-50 TL'),
            ('50-100', '50-100 TL'),
            ('100-250', '100-250 TL'),
            ('250-500', '250-500 TL'),
            ('500-1000', '500-1000 TL'),
            ('1000+', '1000+ TL'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'price-select'}),
        label='Fiyat Aralığı'
    )
    
    min_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Min fiyat',
            'class': 'price-input',
            'min': '0'
        }),
        label='Min Fiyat'
    )
    
    max_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Max fiyat',
            'class': 'price-input',
            'min': '0'
        }),
        label='Max Fiyat'
    )
    
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Şehir',
            'class': 'location-input',
            'data-autocomplete': 'city'
        }),
        label='Şehir'
    )
    
    district = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'İlçe',
            'class': 'location-input',
            'data-autocomplete': 'district'
        }),
        label='İlçe'
    )
    
    distance_range = forms.ChoiceField(
        choices=[
            ('all', 'Tüm Türkiye'),
            ('5', '5 km içinde'),
            ('10', '10 km içinde'),
            ('25', '25 km içinde'),
            ('50', '50 km içinde'),
            ('100', '100 km içinde'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'distance-select'}),
        label='Mesafe'
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'date-input'
        }),
        label='Başlangıç Tarihi'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'date-input'
        }),
        label='Bitiş Tarihi'
    )
    
    has_image = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'feature-checkbox'}),
        label='Sadece fotoğraflı ürünler'
    )
    
    trade_type = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Takas türü (örn: telefon, laptop)',
            'class': 'trade-input'
        }),
        label='Takas Türü'
    )
    
    exclude_own_items = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'feature-checkbox'}),
        label='Kendi ürünlerimi hariç tut'
    )
    
    only_favorites = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'feature-checkbox'}),
        label='Sadece favorilerim'
    )
    
    sort_by = forms.ChoiceField(
        choices=[
            ('newest', 'En Yeni'),
            ('oldest', 'En Eski'),
            ('name_asc', 'A-Z'),
            ('name_desc', 'Z-A'),
            ('price_asc', 'Ucuzdan Pahalıya'),
            ('price_desc', 'Pahalıdan Ucuza'),
            ('distance', 'Yakından Uzağa'),
            ('popularity', 'En Popüler'),
            ('match_score', 'En Uygun'),
        ],
        required=False,
        initial='newest',
        widget=forms.Select(attrs={'class': 'sort-select'}),
        label='Sıralama'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate categories from Item model
        from .models import Item
        self.fields['categories'].choices = Item.CATEGORY_CHOICES
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Price validation
        min_price = cleaned_data.get('min_price')
        max_price = cleaned_data.get('max_price')
        
        if min_price and max_price and min_price > max_price:
            raise forms.ValidationError("Minimum fiyat maksimum fiyattan büyük olamaz.")
        
        # Date validation
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("Başlangıç tarihi bitiş tarihinden sonra olamaz.")
        
        return cleaned_data
    
    def get_search_params(self):
        """Form verilerini arama parametrelerine dönüştür"""
        if not self.is_valid():
            return {}
        
        params = {}
        
        for field_name, value in self.cleaned_data.items():
            if value:  # Skip empty values
                if field_name in ['date_from', 'date_to'] and hasattr(value, 'isoformat'):
                    params[field_name] = value.isoformat()
                else:
                    params[field_name] = value
        
        return params


class SavedSearchForm(forms.Form):
    """Kaydedilmiş arama formu"""
    
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Arama adı (örn: iPhone araması)',
            'class': 'saved-search-name'
        }),
        label='Arama Adı'
    )
    
    set_as_default = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'default-checkbox'}),
        label='Varsayılan arama olarak ayarla'
    )

