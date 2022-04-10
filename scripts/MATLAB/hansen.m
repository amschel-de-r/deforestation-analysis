%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%  Code for deriving deforestation per country  %
%                  (2001-2010)                  %
%            and forest cover in 2000           %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%
% political map (political borders as poygones)
load G:\_GFC\carte_clean.mat
% also possible to use: sphereReference: referenceSphere('earth','km') or wgs84Ellipsoid('km') ;
earthellipsoid =almanac('earth','ellipsoid','kilometers'); 
% 
nom_fichiers_cov=importdata('NomBigPix_stock_all.csv');
nom_fichiers_def=importdata('NomBigPix_all.csv');
latlon=importdata('LatLong_Base_all.csv');
NSEW=importdata('NordSudEstOuest_all.csv');
%
[nb_pix one]=size(nom_fichiers_cov);
n_year=12;
n_pays=246;
GFC_glob=NaN(n_pays,nb_pix,n_year);
cover=NaN(n_pays,nb_pix);
nb_pix_pays=NaN(n_pays,nb_pix);
%
% for j=1:n_pays
% plot(S_country(j).Lon,S_country(j).Lat,'k','linewidth',1.5); % check plus (N & W) & minus (S & E)
% hold on
% end
%
% 180W-180E & 80N-60S  
for i=1:nb_pix;
    i           % display country number
if NSEW(i,1)==1;
lat=latlon(i,1);
else
lat=-latlon(i,1);
end
if NSEW(i,2)==1;
long=latlon(i,2);
else
long=-latlon(i,2);
end
%
LA=flipud([(lat-10):30/3600:lat]');
LO=long:30/3600:(long+10);
%
mat_cov=importdata(char(strcat('G:\_GFC\GFC_treeCover\',nom_fichiers_cov(i,:))));
mat_def=importdata(char(strcat('G:\_GFC\Pixels_GFC\',nom_fichiers_def(i,:))));
% 
cov_25=NaN(30,30);
%
deforest30=NaN(1200,1200,12);
cover30=NaN(1200,1200);
AREA=NaN(1200,1200);
% 30 arc minutes: About 900m2 (30 s/ 30): 
for l=1:1200
for j=1:1200
    %   +0 used to transform to integer: 
cov_25=((mat_cov(((l-1)*30+1):l*30,((j-1)*30+1):j*30))>.25)+0;
cover30(l,j)=(nansum(nansum(cov_25)))/900;
% ~=1km pixel area
AREA(l,j)=areaquad(LA(l),LO(j),LA(l+1),LO(j+1),earthellipsoid);
    for k=1:12 % agregation of 30arc second pixels of annual deforestation into ~=1 squared km averages
def=(mat_def(((l-1)*30+1):l*30,((j-1)*30+1):j*30)==k)+0;
deforest30(l,j,k)=(nansum(nansum((cov_25.*def))))/900;
    end
end
end
filename = ['cover_deforest_30m_fin_' num2str(i) '.mat' ];
save(filename,'deforest30','cover30','AREA');
% char(strcat('G:\_GFC\GFC_treeCover\',nom_fichiers(i,:))).mat
INPOL=NaN(1200,1200); % matrix =1 if inside borders of country P: 
    for p=1:n_pays
if nanmax(LA)<nanmin(S_country(p).Lat) || nanmin(LA)>nanmax(S_country(p).Lat) || nanmax(LO)<nanmin(S_country(p).Lon) || nanmin(LO)>nanmax(S_country(p).Lon)
else
    INPOL(:,:)=inpolygon(ones(1200,1)*LO(1,1:1200),LA(1:1200,1)*ones(1,1200),S_country(p).Lon',S_country(p).Lat')+0;
% number of pixels within country P: 
nb_pix_pays(p,i)=nansum(nansum(INPOL));
cover(p,i)=nansum(nansum(INPOL.*(cover30.*AREA)));
for k=1:12
GFC_glob(p,i,k)=nansum(nansum(INPOL.*(deforest30(:,:,k).*AREA),1),2);
end
%
end 
clear INPOL
    end
    % clear useless variables to earn disk space
clear mat_cov mat_def deforest30 cover30 AREA
save GFC_outG.mat
save GFC_out.mat GFC_glob nb_pix_pays cover
end  
save GFC_outG.mat
save GFC_out.mat GFC_glob nb_pix_pays cover

% optional for office worksheet compatible format outputs:
% csvwrite(GFC_out.csv,GFC_glob)
% csvwrite(nb_pix_out.csv,nb_pix_pays)