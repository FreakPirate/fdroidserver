
%w{ant ant-contrib maven javacc python git-core mercurial subversion bzr git-svn make perlmagick}.each do |pkg|
  package pkg do
    action :install
  end
end

