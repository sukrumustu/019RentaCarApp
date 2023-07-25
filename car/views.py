from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from .models import Car, Reservation
from .serializers import CarSerializer, ReservationSerializer
from .permissions import IsStaffOrReadOnly
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone


from django.db.models import Q


class CarView(ModelViewSet):
    queryset = Car.objects.all()
    serializer_class = CarSerializer
    permission_classes = (IsStaffOrReadOnly,)
    
    
    # bu metodun overwrite ile 1. Car'a ait bir tarih aralığı sorgusu geldiğinde a. staff-user tüm available olan ve olmayanları görebiliyor. Ancak standart user ise ancak o tarih aralığında yalnızca available olanları görebiliyor. Burada Q ile conditionlarbelirledik. Buna göre  "...car/?start=2023-06-15?end=2023-06-20" şeklinde gelen querylerde start ve end tarihleri rezerve edilmiş carların start_date ve end_date leri ile birebir karşılaştırılarak unavailable olanlar filtrelenerek listeden çıkartılıyor. Burada url'de soru işaretinden sonra gelen key'lere(start-end veya from-to ...) param deniyor ve request.query_params.get('start') şeklinde ulaşılabiliyor. İkinci yolu clarusway folderında mevcut.Oraya da bak.
    
    def get_queryset(self):
        if self.request.user.is_staff:
            queryset = super().get_queryset()
        else:
            queryset = super().get_queryset().filter(availability = True)
        start = self.request.query_params.get('start')     
        end = self.request.query_params.get('end')
        
        if start is not None or end is not None:   #burayı eğer start ve end paramları girilmişse çalıştır diyoruz.   ...api/car/ girdiğimde none hatası vermesin diye. Böylece tüm araçlar gelir. normalde frontend de böyle gösterilmez. 
        
            # buradaki conditionlar başka start_date ve end_date i olan modeller için de kullanılabilir. İstersek cond1 ve cond2 yazmadan doğrudan Q'lu halini de yazabiliriz.
            cond1 = Q(start_date__lt=end)
            cond2 = Q(end_date__gt=start)
            not_available = Reservation.objects.filter(cond1 & cond2).values_list('car_id', flat=True)
        
            queryset = queryset.exclude(id__in = not_available)
    
    
    
            
    # eğer serializersda userın görmesini istemediğimiz fieldlerini göndermek istemiyorsak ya orada tek serializer içinde tanımladığımız yolu kullanacağız veya orada staff için ayrı user için ayrı iki farklı serializer tanımlayıp buraya aşağıdaki şekilde koyacağız. 
           
    # def get_serializer_class(self):
    #     if self.request.user.is_staff:
    #         return CarStaffSerializer
    #     else:
    #         return CarSerializer
        
        return queryset
    

class ReservationView(ListCreateAPIView):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    permission_classes = (IsAuthenticated,)
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return super().get_queryset()
        return super().get_queryset().filter(customer=self.request.user)
    

class ReservationDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Reservation.objects.all()
    serializer_class=ReservationSerializer
    # lookup_field='id'
    
    #bu override ile bir rezervasyonu update ederken eğer rezervasyonun enddateni artırmak istiyorsam o tarihler içerisinde aynı arabanın başka rezervasyonu olup olmadığını kontrol ediyorum. Yoksa normal update işlemini yapıyorum. 
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        end = serializer.validated_data.get('end_date')
        car = serializer.validated_data.get('car')
        start = instance.start_date
        today = timezone.now().date()
        if Reservation.objects.filter(car=car).exists():
            # a = Reservation.objects.filter(car=car, start_date__gte=today)
            # print(len(a))
            for res in Reservation.objects.filter(car=car, end_date__gte=today):
                if start < res.start_date < end:
                    return Response({'message': 'Car is not available...'})

        return super().update(request, *args, **kwargs)

